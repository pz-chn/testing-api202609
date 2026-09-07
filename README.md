# api

這是一個「台股資料 API 服務」的教學專案，帶你學會如何用 FastAPI 把資料庫裡的股價資料包成 HTTP API，提供給前端、App、或其他服務查詢。

## 這個專案在做什麼？

整個流程像這樣：

```
使用者 / 前端  →  HTTP 請求  →  FastAPI (這個專案)  →  SQL 查詢  →  MySQL  →  回傳 JSON
```

- **使用者**：在瀏覽器或程式中發出請求，例如 `GET /taiwan_stock_price?stock_id=2330&start_date=2024-01-01&end_date=2024-12-31`
- **FastAPI**：接收請求、解析參數、組 SQL、查 DB、把結果包成 JSON 回傳
- **MySQL**：實際存放股價資料的地方（由 `crawler` 專案爬下來寫入）

> 這個 api 專案是 `crawler` 專案的「下游」：crawler 把資料寫進 MySQL，api 再把資料拿出來給人查。兩個專案合起來才是完整的一條資料管線。

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/94ef7261-4744-4cd1-9fb5-88b81b5439b6" />


## 為什麼要做成 API？

初學者可能會想：「我直接連 MySQL 撈資料不就好了嗎？」

是可以，但當你面對以下情境就會卡住：
- **不想讓使用者直接碰 DB**：給帳密太危險，給了還無法限制查詢範圍
- **要給前端 / App 用**：前端通常無法直連 DB，必須透過 HTTP
- **要做權限、限流、快取**：這些只能在中間層（API）實作
- **要切換資料來源**：今天 MySQL、明天 BigQuery，API 把這層細節包起來，前端不用改

所以業界都會用 **FastAPI / Flask / Django** 這類 Web 框架，把資料庫包在後面，對外只開放 HTTP 介面。

## 使用的技術

| 技術 | 用途 | 為什麼用它 |
| --- | --- | --- |
| Python 3.11 | 主要開發語言 | 生態最豐富 |
| [uv](https://docs.astral.sh/uv/) | 套件管理 | 比 pip/pipenv 快 10～100 倍 |
| [FastAPI](https://fastapi.tiangolo.com/) | Web 框架 | 自動產生 Swagger 文件、效能好、type hint 友善 |
| [Uvicorn](https://www.uvicorn.org/) | ASGI Server | 跑 FastAPI 的伺服器，支援 async |
| [SQLAlchemy](https://www.sqlalchemy.org/) | ORM / DB 連線 | 用 Python 操作資料庫 |
| [PyMySQL](https://pymysql.readthedocs.io/) | MySQL driver | SQLAlchemy 連 MySQL 的底層套件 |
| [Pandas](https://pandas.pydata.org/) | 資料處理 | 把 SQL 結果轉成 DataFrame，方便輸出 JSON |
| [Loguru](https://loguru.readthedocs.io/) | Logging | 比內建 logging 簡單好用 |
| Docker + Docker Compose | 容器化部署 | 一鍵啟動、跨平台 |

## 資料夾結構速覽

```
api/
├── api/
│   ├── __init__.py                      # 把資料夾標記成 Python package
│   ├── config.py                        # 環境變數集中管理（DB host、帳密…）
│   └── main.py                          # FastAPI 主程式 (路由 + DB 查詢)
├── genenv.py                            # 從 local.ini 產生 .env
├── local.ini                            # 各環境設定（DEV / DOCKER / PRODUCTION）
├── pyproject.toml                       # 套件定義（專案 metadata + 依賴清單）
├── uv.lock                              # 鎖定每個套件的精確版本
├── with.env.Dockerfile                  # Docker 映像建置腳本
└── docker-compose-api-network-version.yml  # 啟動 api container 的設定
```

### 為什麼把程式放在 `api/` 子資料夾？

你可能看過一些教學把 `main.py` 直接放在專案根目錄，為什麼這個專案要多包一層 `api/`？

- **import 路徑跟正式環境一致**：把程式放在 `api/`，搭配 `pyproject.toml` 的 `packages = ["api"]`，執行 `uv sync` 會把它「裝成套件」，不管在開發機或 Docker 容器內，都用同一條 `from api.config import ...` import 路徑。
- **package 名稱 = 對外的識別**：`uvicorn api.main:app` 這串裡的 `api` 就是這個 package 名稱，把程式集中在同名資料夾下，路徑與名稱一目了然。

## 學習順序建議

如果你是第一次接觸這個專案，建議依序閱讀：

1. `pyproject.toml` — 看專案需要哪些套件
2. `local.ini` + `genenv.py` — 了解環境變數怎麼從 ini 檔轉成 `.env`
3. `api/config.py` — 看程式怎麼讀環境變數
4. `api/main.py` — 認識 FastAPI 路由與 DB 查詢的最小範例
5. `with.env.Dockerfile` — 學習怎麼把 API 包進 Docker
6. `docker-compose-api-network-version.yml` — 把 API 跟其他服務（MySQL）串起來

## 環境變數的流動（重要）

新手最容易卡住的地方：「為什麼程式裡寫 `MYSQL_HOST = os.environ.get(...)`，這個值到底從哪來？」

整條鏈是這樣：

```
local.ini  ──(genenv.py 讀)──►  .env  ──(uv run --env-file)──►  os.environ  ──(config.py 讀)──►  main.py 使用
```

#### Step 1: `local.ini` 定義「不同環境的設定值」

```ini
[DEV]
MYSQL_HOST = 127.0.0.1     # 本機開發連 localhost

[DOCKER]
MYSQL_HOST = mysql          # 容器內用 service 名稱當 hostname

[PRODUCTION]
MYSQL_HOST = production_host  # 正式機真實位址
```

同一個 key（`MYSQL_HOST`）在三個區段有三個值，這就是「同一份程式碼跑在不同環境」的關鍵。

#### Step 2: `genenv.py` 把指定區段轉成 `.env`

```bash
ENV=DEV python genenv.py
```

這會讀 `local.ini` 的 `[DEV]` 區段，產生：

```
# .env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
...
```

換 `ENV=DOCKER` 就會產生 `MYSQL_HOST=mysql` 的 `.env`。**`genenv.py` 是「環境切換器」**。

#### Step 3: `uv run --env-file=.env` 把 `.env` 載入 `os.environ`

```bash
uv run --env-file=.env uvicorn api.main:app
```

`--env-file` 是 uv 的功能，會在跑指令前把 `.env` 的 key=value 塞進 `os.environ`。

#### Step 4: `config.py` 從 `os.environ` 讀出來

```python
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")  # 後面的值是 fallback
```

#### Step 5: `main.py` import 來用

```python
from api.config import MYSQL_HOST, MYSQL_PORT, ...
address = f"mysql+pymysql://{...}@{MYSQL_HOST}:{MYSQL_PORT}/mydb"
```

**為什麼要這麼多層？** 把「設定」跟「程式」分開，同一份程式碼可以跑在 dev / docker / prod，只要換 `.env` 就好，不用改程式。

## `pyproject.toml` + `uv.lock` 說明

`pyproject.toml` 是 Python 專案的「身分證」，宣告：
- 專案名稱、版本、作者
- 需要的 Python 版本（`>=3.11`）
- 依賴的套件清單（FastAPI、SQLAlchemy…）
- 怎麼打包（`hatchling` + `packages = ["api"]`）

`uv.lock` 則是「鎖檔」，紀錄每個套件**實際裝下來的精確版本**（連間接依賴也鎖死）。

| 檔案 | 角色 | 誰會看 |
| --- | --- | --- |
| `pyproject.toml` | 你寫的「我要這些套件」 | 人類、uv |
| `uv.lock` | uv 算出的「實際裝這些版本」 | uv（用來重現一模一樣的環境） |

兩個都要進 git。`uv sync --frozen` 會嚴格按 `uv.lock` 安裝，這就是為什麼 Dockerfile 用 `--frozen`：保證正式機跟開發機裝到一模一樣的版本。

## `main.py` 程式碼導讀

整支只有 50 行，但濃縮了一個完整 API 的所有元素：

```python
# 1. 建立 FastAPI 實例
app = FastAPI()

# 2. 定義「DB 連線」這個工具函式
def get_mysql_financialdata_conn():
    address = f"mysql+pymysql://{MYSQL_ACCOUNT}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/mydb"
    return create_engine(address).connect()

# 3. 註冊路由：URL → 函式
@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/taiwan_stock_price")
def taiwan_stock_price(stock_id: str = "", start_date: str = "", end_date: str = ""):
    # 3a. 組 SQL
    sql = f"select * from taiwan_stock_price where StockID = '{stock_id}' ..."
    # 3b. 查 DB
    mysql_conn = get_mysql_financialdata_conn()
    data_df = pd.read_sql(sql, con=mysql_conn)
    # 3c. 包成 JSON 回傳
    return {"data": data_df.to_dict("records")}
```

**幾個值得學的觀念：**

- `@app.get("/xxx")` 是 **decorator**，把下面的函式註冊成 GET `/xxx` 的處理器。FastAPI 會自動把 query string（`?stock_id=2330`）解析成函式參數。
- 函式參數寫 type hint（`stock_id: str`），FastAPI 會自動轉型 + 自動產生 Swagger 文件。
- `pd.read_sql(sql, conn)` 一行就把 SQL 結果變成 DataFrame，再 `.to_dict("records")` 轉成 `[{...}, {...}]` 這種前端最愛的格式。

> ⚠️ **教學提醒**：這份範例為了簡單直觀，用 f-string 把參數塞進 SQL，**正式環境會有 SQL injection 風險**。實務上應該用 SQLAlchemy 的 parameterized query（`text("... where StockID = :stock_id")`）或 ORM。這個專案先學會骨架，安全強化是下一步。

## API endpoint 速覽

啟動後可在瀏覽器打開 `http://localhost:8888/docs` 看自動產生的 Swagger 文件（**FastAPI 最強的賣點之一，不用自己寫文件**）。

| Method | Path | 說明 |
| --- | --- | --- |
| GET | `/` | 健康檢查，回 `{"Hello": "World"}` |
| GET | `/taiwan_stock_price` | 查詢個股區間股價，參數：`stock_id`、`start_date`、`end_date` |

### 測試 API 的三種方式

**1. 瀏覽器直接打：**

```
http://localhost:8888/taiwan_stock_price?stock_id=2330&start_date=2024-01-01&end_date=2024-01-31
```

**2. curl：**

```bash
curl "http://localhost:8888/taiwan_stock_price?stock_id=2330&start_date=2024-01-01&end_date=2024-01-31"
```

**3. Python requests：**

```python
import requests
res = requests.get(
    "http://localhost:8888/taiwan_stock_price",
    params={"stock_id": "2330", "start_date": "2024-01-01", "end_date": "2024-01-31"},
)
print(res.json())
```

**4. Swagger UI（推薦初學者）：** 打開 `http://localhost:8888/docs`，點任何一個 endpoint → 「Try it out」→ 填參數 → 「Execute」，可視化測試 + 自動顯示 curl 指令。

## Dockerfile 說明

`with.env.Dockerfile` 內部流程：

```
FROM ubuntu:22.04               ← 從乾淨的 Ubuntu 開始
→ 安裝 curl、ca-certificates    ← 下載 uv 需要的工具
→ 安裝 uv                       ← Python 套件管理工具
→ 安裝 Python 3.11              ← 指定 Python 版本
→ COPY 專案檔案進容器（api、pyproject.toml、uv.lock、local.ini…）
→ uv sync --frozen              ← 根據 uv.lock 安裝所有套件（確保版本一致）
→ 設定 UTF-8 語系              ← 避免中文編碼問題
→ ENV=DOCKER uv run python genenv.py  ← 產生 docker 環境的 .env
→ CMD bash                      ← 預設進入 bash（compose 啟動時會覆寫成 uvicorn 指令）
```

**為什麼要 `uv sync --frozen`？**
`--frozen` 會嚴格按照 `uv.lock` 的版本安裝，不會自己去解析最新版。這樣才能保證「開發機」跟「正式機」裝到的是一模一樣的套件版本，避免「我這裡跑得好好的」這種問題。

**為什麼 build 時就要產生 `.env`？**
方便：image 推到正式機後不用再手動建環境變數，container 起來就能跑。代價是不同環境（DOCKER / PRODUCTION）要各自 build 一份 image，所以才有 `with.env.Dockerfile` 跟 `prod.with.env.Dockerfile` 之分（這個專案目前只有 `with.env.Dockerfile`）。

## docker-compose 說明

`docker-compose-api-network-version.yml` 重點：

| 設定 | 意義 |
| --- | --- |
| `image: linsamtw/tibame_api:${DOCKER_IMAGE_VERSION}` | image 版本透過環境變數帶入，方便切換版本 |
| `command: uvicorn api.main:app ...` | 容器啟動後執行的指令（覆寫 Dockerfile 的 CMD） |
| `ports: 8888:8888` | 把容器內 8888 port 對應到主機 8888 |
| `networks: my_network` | 加入外部 `my_network`，才能跟 MySQL container 互通 |
| `restart: always` | 容器掛掉自動重啟 |
| `external: true` | 表示這個 network 不是 compose 自己建的，是事先用 `docker network create` 建好的 |

**為什麼要用外部 `my_network`？**
因為 MySQL 是另一個 compose 檔（`crawler/mysql.yml`）啟動的 container。要讓 api container 用 hostname `mysql` 連到 DB，兩邊必須在同一個 docker 網路。所以先 `docker network create my_network`，兩邊都加進去。

### 典型啟動順序（含上游 MySQL）

```bash
# 1. 建立共用網路（只要做一次）
docker network create my_network

# 2. 啟動 MySQL（在 crawler/ 目錄底下）
cd ../crawler
docker compose -f mysql.yml up -d

# 3. （可選）先用 crawler 把資料灌進 MySQL
DOCKER_IMAGE_VERSION=0.0.6 docker compose -f docker-compose-worker-network-version.yml up -d
DOCKER_IMAGE_VERSION=0.0.6 docker compose -f docker-compose-producer-network-version.yml up -d

# 4. 回到 api/ 啟動 API 服務
cd ../api
DOCKER_IMAGE_VERSION=0.0.1 docker compose -f docker-compose-api-network-version.yml up -d

# 5. 驗證
curl http://localhost:8888/
# 預期回傳 {"Hello":"World"}
```

## .gitignore 說明

`.gitignore` 列出「不要被 git 追蹤的檔案/資料夾」，避免意外把敏感資料或垃圾檔案推上 GitHub。

| 項目 | 為什麼要忽略 |
| --- | --- |
| `*__pycache__/`、`*.pyc` | Python 編譯產生的暫存檔，換台電腦重新產生就好 |
| `.vscode/`、`*.vscode` | 編輯器個人設定，每個人習慣不同 |
| `*.pytest_cache/` | pytest 的快取 |
| `.env` | **最重要！** 裡面有資料庫帳密，絕不能進 git |
| `*.egg-info`、`build/` | Python 打包產生的檔案 |
| `.cache` | 各種工具的暫存 |

**新手常見錯誤**：把 `.env` 推上 public repo，幾分鐘內密碼就會被掃到外洩。養成習慣：加 `.env` 進 `.gitignore` **永遠是第一步**。

---

# 環境設定

#### 安裝 uv

    curl -LsSf https://astral.sh/uv/install.sh | sh

#### 安裝 Python 3.11

    uv python install 3.11

#### set uv 虛擬環境

    uv venv --python 3.11

#### 安裝 repo 套件

    uv sync

#### 建立環境變數

    ENV=DEV python genenv.py
    ENV=DOCKER python genenv.py
    ENV=PRODUCTION python genenv.py

#### 排版

    black -l 80 api/

# API

#### 啟動 fastapi

    uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8888

啟動後可開：
- `http://localhost:8888/` — 確認服務有起來
- `http://localhost:8888/docs` — Swagger 互動式 API 文件
- `http://localhost:8888/redoc` — ReDoc 風格的 API 文件

#### `uvicorn api.main:app` 這串怎麼解讀？

- `api.main` — Python module 路徑，對應到 `api/main.py`
- `:app` — 該檔案裡名為 `app` 的物件（`app = FastAPI()`）
- `--reload` — 程式碼有改動就自動重啟（**只在開發用**，正式環境拿掉）
- `--host 0.0.0.0` — 監聽所有網卡（不寫的話只能 localhost 連，container 外連不到）
- `--port 8888` — 指定 port

# Docker

#### 建立 network（只要做一次）

    docker network create my_network

#### build docker image

    docker build -f with.env.Dockerfile -t linsamtw/tibame_api:0.0.1 .
    docker build -f with.env.Dockerfile --platform linux/arm64 -t linsamtw/tibame_api:0.0.1.arm64 .

#### push docker image

    docker push linsamtw/tibame_api:0.0.1
    docker push linsamtw/tibame_api:0.0.1.arm64

#### 啟動 api

    DOCKER_IMAGE_VERSION=0.0.1 docker compose -f docker-compose-api-network-version.yml up -d

#### 關閉 api

    DOCKER_IMAGE_VERSION=0.0.1 docker compose -f docker-compose-api-network-version.yml down

#### 查看 docker container 狀況

    docker ps -a

#### 查看 log（除錯必備）

    docker logs api          # 看完整 log
    docker logs -f api       # 持續追蹤新 log（Ctrl+C 離開）
    docker logs --tail 50 api  # 只看最後 50 行
