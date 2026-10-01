# 匯入相關套件
import pandas as pd  # 用來處理資料表，把 SQL 查詢結果轉成 DataFrame
from fastapi import FastAPI  # FastAPI 主類別，建立 Web 應用實例
from sqlalchemy import create_engine, engine  # 建立 DB 連線與引擎

# 匯入自定義的資料庫連線設定（從 config.py 來，最終源頭是 .env）
from api.config import MYSQL_ACCOUNT, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT


# 建立連接到 MySQL 資料庫的函式，回傳一個 SQLAlchemy 的連線物件
# 抽成函式的好處：每個 API 路由都可以呼叫，不用重複寫連線字串
def get_mysql_financialdata_conn() -> engine.base.Connection:
    # 組成資料庫連線字串，格式：mysql+pymysql://帳號:密碼@host:port/資料庫名
    # mysql+pymysql 表示用 SQLAlchemy 介面 + PyMySQL 當底層 driver
    address = f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/test_mygopen"
    engine = create_engine(address)  # 建立 SQLAlchemy 引擎（管理連線池）
    connect = engine.connect()  # 從引擎拿一條實際的連線
    return connect  # 回傳連線物件，外面就能拿來執行 SQL


# 建立 FastAPI 應用實例
# 這個 app 物件就是整個 API 的核心，後面所有路由都註冊在它身上
# uvicorn 啟動時會找這個變數：uvicorn api.main:app 中的 :app 就是指這個
app = FastAPI()


# 定義根目錄路由（測試用）
# @app.get("/") 是 decorator，把下面這個函式註冊成「GET / 的處理器」
# 開瀏覽器打 http://localhost:8888/ 就會執行下面的 read_root()
@app.get("/")
def read_root():
    return {"Hello": "World"}  # FastAPI 會自動把 dict 轉成 JSON 回傳


# 定義取得台灣股價的 API 路由
# 函式參數會自動對應到 URL 的 query string
# 例如 /taiwan_stock_price?stock_id=2330&start_date=2024-01-01
# stock_id="" 表示沒帶就預設空字串
@app.get("/test_mygopen")
def test_mygopen(
    dscp: str = "",  # 股票代號（可透過 URL query string 傳入）
):
    # 根據參數組成 SQL 查詢語句
    # 注意：這裡用 f-string 直接拼接是為了教學易讀
    # 正式環境要改用 parameterized query 防止 SQL injection
    sql = f"""
    select * from mygopen_articles
    where published LIKE '%%{dscp}%%'
    or content_text LIKE '%%{dscp}%%'
    """
    # 建立資料庫連線
    mysql_conn = get_mysql_financialdata_conn()
    # 使用 Pandas 執行 SQL 查詢並取得資料
    # pd.read_sql 一行就把查詢結果包成 DataFrame，省下手動 cursor.fetchall + 轉欄位
    data_df = pd.read_sql(sql, con=mysql_conn)
    # 將 DataFrame 轉為 List of Dict 格式，方便 FastAPI 回傳 JSON
    # records 模式會產出 [{欄位:值, ...}, {欄位:值, ...}] 這種前端最愛吃的結構
    data_dict = data_df.to_dict("records")
    return {"data": data_dict}  # 回傳資料結果（FastAPI 自動序列化成 JSON）
