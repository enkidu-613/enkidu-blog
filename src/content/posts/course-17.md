---
title: "17. JWT 用户认证"
published: 2026-01-17
description: "JWT 是一张服务器盖章的数字身份卡。服务器不用记你是谁，只看这张卡的印章对不对、过期了没。"
tags: ["AI 应用工程", "学习笔记"]
category: "AI 应用工程"
draft: false
---
> **这不是用来"背"的安全手册，这是你放在桌面上的外挂菜单。**
> 忘了 JWT 怎么传？`Ctrl+F` 搜"Bearer"，看比喻，抄模板。

---

## 🧠 ADHD 四条铁律（先读！）

| # | 铁律 | 本章怎么做 |
|---|------|-----------|
| 1 | **绝不从头写代码** | 打开 `app/routers/auth.py`，复制 `get_current_user` → 粘贴到你的路由里 |
| 2 | **报错看最后一行** | 401 就是票不对，403 就是权限不够，500 找堆栈最后一行 |
| 3 | **不懂就跳过** | 长短 Token 暂时只理解概念，先跑通单 Token + 黑名单 |
| 4 | **拥抱 JSON** | `{"access_token": "...", "token_type": "bearer"}` 就是登录返回的字典 |

---

## 🎯 一句话理解

JWT 是一张**服务器盖章的数字身份卡**。服务器不用记你是谁，只看这张卡的印章对不对、过期了没。

## 🗺️ 本章代码地图

> 边读边对照项目文件，ADHD 友好——看到真实代码比读文档安心 10 倍。

| 学到什么 | 对应文件 | 关键代码行 |
|----------|---------|-----------|
| User 表 & RevokedToken 表 | `models.py:17-35` | `class User(Base)`, `class RevokedToken(Base)` |
| JWT 签发 / 验证 / 黑名单 | `app/routers/auth.py:54-69` | `create_token()`, `_hash_token()` |
| 自动验票机 | `app/routers/auth.py:73-97` | `def get_current_user(...)` |
| 角色守卫 | `app/routers/auth.py:101-112` | `def require_role(*allowed_roles)` |
| 注册 / 登录 / 登出 | `app/routers/auth.py:116-179` | `/auth/register`, `/auth/login`, `/auth/logout` |
| 路由注册 & Swagger | `main.py:84` | `app.include_router(auth_router.router)` |
| CORS & 异常处理 | `main.py:60-76` | `CORSMiddleware`, `global_exception_handler` |

---

## 📖 第一关：认证 vs 授权

### 一句话
- **认证**：查身份证（你是谁？）
- **授权**：看门禁权限（你能进哪间房？）

### 生活类比
想象你进一栋写字楼：
1. **前台查身份证** → 认证（Authentication）→ 没身份证？滚出去（401）
2. **闸机刷门禁卡** → 授权（Authorization）→ 身份证对了但只能去3楼，你按5楼？拒绝（403）

```
你 → [前台: 有身份证?] → [闸机: 能去5楼?] → 进办公室
      ↓ 没有               ↓ 不能
    401 Unauthorized     403 Forbidden
```

> **记住口诀**：401 是"没身份"，403 是"有身份但没权限"。

### ✅ 检查点
- [ ] 用自己的话说：一个人带了身份证但不是 VIP，他访问 VIP 区返回 401 还是 403？为什么？

---

## 📖 第二关：密码绝不能存明文

### 一句话
哈希是**单向绞肉机**：密码进去，变成一团认不出的肉泥，而且倒不回去。

### 生活类比
你在家做一道"秘制酱料"：
- 把牛肉、辣椒、盐扔进绞肉机（哈希函数）
- 出来的是肉泥（哈希值）
- 给你这团肉泥，你能反推出用了多少克盐吗？**不可能。**
- 而且每次加盐量不同（Salt），同样的牛肉进去，出来的肉泥也不一样

### 💻 代码示例

```python
import bcrypt

# ========== 注册时 ==========
hashed = bcrypt.hashpw(
    b"myPassword123",
    bcrypt.gensalt(rounds=10)  # rounds=10 故意变慢 ~100ms，增加暴力破解成本
)
# 存进数据库的：b'$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZIMs3xXcJ3...'

# ========== 登录时 ==========
is_valid = bcrypt.checkpw(b"myPassword123", hashed)
# True → 密码正确，False → 密码错误
```

### 🔍 逐步拆解
1. `bcrypt.gensalt(rounds=10)` — 生成随机盐，"rounds=10" 让哈希故意慢到 ~100ms
2. `bcrypt.hashpw(...)` — 密码 + 盐 → 肉泥，结果里自带盐值（不用单独存盐）
3. `bcrypt.checkpw(...)` — 从存库的肉泥里提取盐，用同样盐对新输入做哈希，比对结果
4. **为什么要慢？** 攻击者暴力破解时每个密码都要花 100ms，100 万个就花 27 小时

### ⚠️ 常见错误
| 错误 | 原因 | 正确做法 |
|------|------|----------|
| 存明文密码 | 数据库一泄露，全网账号沦陷 | 永远只存 `bcrypt.hashpw` 的结果 |
| 自己写加密算法 | 你写的密码学 = 裸奔 | 用 `bcrypt`、`argon2`、`scrypt`，别发明轮子 |
| 登录提示"密码错误"而非"账号或密码错误" | 暴露账号存在性，方便撞库 | 统一提示"账号或密码错误" |

### 📋 速查表
```python
# 注册
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10))

# 登录
is_ok = bcrypt.checkpw(password.encode(), stored_hash.encode())
```

### ✅ 检查点
- [ ] bcrypt 的 "salt" 是干嘛的？为什么同一个密码两次 hashpw 结果不同？
- [ ] `rounds=10` 是什么意思？为什么不是越大越好？

---

### 🔬 bcrypt hash 内部解剖（盐、成本因子、版本号）

生成出来的 hash 不是一串乱码，它有严格的 60 字符结构：

```
$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZIMs3xXcJ3xMBXmq...
 ─┬─ ─┬─ ───────────┬────────────── ──────────┬──────────
  │   │       盐 (22 字符)              哈希值 (31 字符)
  │   └─ 成本因子 rounds=10 → 2^10 = 1024 次迭代
  └───── 版本号 $2b$
```

#### 🧂 盐（Salt）—— 22 字符

- **来源**：`bcrypt.gensalt()` 调用操作系统的加密安全随机数生成器（Linux 读 `/dev/urandom`，macOS 用 Security.framework）
- **作用**：即使两个用户密码相同，因为盐不同，最终 hash 完全不同
- **不用单独存**：盐直接嵌在 hash 字符串前 22 字符里，验证时 checkpw 自动提取

#### 🔢 成本因子（Cost Factor）—— `$10$`

- `rounds=10` 意思是 **2^10 = 1024 次**迭代哈希
- `rounds=12` → 2^12 = **4096 次**，是 rounds=10 的 **4 倍**
- `rounds=14` → 2^14 = **16384 次**，是 rounds=10 的 **16 倍**

> ⚠️ **为什么不是越大越好？** 成本因子每 +1，哈希时间翻倍。rounds=14 会让每次登录等 ~1.6 秒，用户体验崩了。业界建议让 hash 耗时控制在 **100ms~300ms**，根据服务器性能调。

| rounds | 迭代次数 | 大致耗时 | 适合场景 |
|:------:|:--------:|:--------:|----------|
| 8 | 256 | ~6ms | ❌ 太弱 |
| **10** | **1024** | **~100ms** | ✅ 学习/一般应用 |
| 12 | 4096 | ~400ms | 生产环境推荐 |
| 14 | 16384 | ~1.6s | ⚠️ 高安全但慢 |

#### 📜 版本号 —— `$2b$`

bcrypt 有不同的算法版本：

| 版本 | 含义 |
|:----:|------|
| `$2a$` | 原始版本，存在一个 2011 年发现的溢出 bug（密码超 55 字符时被截断） |
| `$2b$` | **修复版**（2014），修正了 `$2a$` 的截断 bug，当前默认 |
| `$2y$` | PHP 早期对 `$2b$` 的别名，实际等价 |
| `$2x$` | PHP 的"bug-compatible"模式，刻意保留 `$2a$` 的 bug |

你的项目用的是 `$2b$`（`bcrypt.gensalt()` 默认），这是正确的现代选择。

---

## 📖 第三关：JWT 是一张三段式防伪门票

### 一句话
JWT = `Header（票头）.Payload（票面信息）.Signature（防伪钢印）`

### 生活类比
想象一张演唱会门票：
- **票头**：印着"本场演出 + 验票方式"（Header: `{"alg":"HS256","typ":"JWT"}`）
- **票面**：印着"座位号 + 票价 + 有效日期"（Payload: 用户ID、角色、过期时间）
- **防伪钢印**：场馆用私章盖上去的（Signature: `HMAC-SHA256(Header.Payload, SECRET)`）

**🚨 关键警醒**：票面信息（Payload）只是 Base64 编码——不是加密！任何人在 jwt.io 粘贴就能解码。**绝不要在 Payload 里放密码/手机号！**

### 💻 代码示例——你的项目里 [app/routers/auth.py:54-64](app/routers/auth.py)

```python
import jwt
from datetime import datetime, timedelta, timezone

JWT_SECRET = os.getenv("JWT_SECRET")   # ← 生产环境必须走环境变量！
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 2

def create_token(user_id: int, username: str, role: str) -> str:
    """签发 JWT 门票"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),       # subject = 谁的门票
        "username": username,      # 购票人
        "role": role,              # VIP区还是普通区
        "iat": now,                # issued at = 签发时间
        "exp": now + timedelta(hours=JWT_EXPIRES_HOURS),  # 2小时后过期
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# 结果长这样：
# eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidXNlcm5hbWUiOiJqb2huIn0.xxxxxx
#  ↑ Header              ↑ Payload                    ↑ Signature
```

### 🔍 逐步拆解
1. `"sub"` = subject，约定俗成放用户 ID（字符串格式）
2. `"iat"` = issued at，签发时间戳
3. `"exp"` = expiration，**必须设！** 不然 Token 永不过期
4. `jwt.encode(payload, SECRET, algorithm)` — 三个参数缺一不可

### ⚠️ 常见错误
| 错误 | 后果 | 正确做法 |
|------|------|----------|
| Payload 放敏感信息 | Base64 可解码，等于明信片写密码 | 只放用户ID、角色、过期时间 |
| JWT_SECRET 硬编码在代码里 | 源码泄露 = 全世界可伪造你 Token | `os.getenv("JWT_SECRET")` |
| 不设 `exp` 过期时间 | Token 一旦发出，**永不过期** | 永远加 `exp` |

### 📋 速查表
```python
# 签发
payload = {
    "sub": str(user_id), "role": role,
    "iat": datetime.now(timezone.utc),
    "exp": datetime.now(timezone.utc) + timedelta(hours=2)
}
token = jwt.encode(payload, SECRET, algorithm="HS256")

# 验证
try:
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
except jwt.ExpiredSignatureError:
    # 门票过期了
except jwt.InvalidTokenError:
    # 假票！
```

### ✅ 检查点
- [ ] JWT 三段分别是什么？哪段是 Base64 裸奔的？
- [ ] 为什么 Payload 不能放密码？
- [ ] `sub`、`iat`、`exp` 分别是什么意思？

---

## 📖 第四关：配置安全 —— 十二因子原则

### 一句话
**JWT_SECRET 是后端最敏感的配置**，绝不能写死在代码里。代码是菜谱，配置是盐——不同环境放不同的量。

### 生活类比
连锁餐厅：
- **代码** = 招牌菜做法（所有分店一样）
- **配置** = 每分店的后厨密码、地址（每家不同）
- 能把后厨密码印在菜谱上发给所有人吗？**不能。**

### 💻 代码示例——你的项目 [app/routers/auth.py:24-29](app/routers/auth.py)

```python
import os

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = 2

# 🔥 fail-fast：没密钥直接崩溃，绝不带病运行
if not JWT_SECRET:
    raise ValueError("❌ JWT_SECRET 环境变量未设置，服务器拒绝启动！")
```

```bash
# .env 文件（本地开发用，绝不提交到 Git！）
JWT_SECRET=your-random-secret-at-least-32-chars
```

### 🔍 逐步拆解
1. **代码与配置分离**：代码里只有 `os.getenv`，没有真密钥
2. **环境变量注入**：本地用 `.env`，生产用云秘钥管理（AWS Secrets Manager / 阿里云 KMS）
3. **.env 不加 Git**：一提交，密钥永久留在 Git 历史，删都删不掉
4. **启动时 crash**（fail-fast）：与其拿空字符串签名 Token（等于没锁门），不如直接拒绝启动

### 📋 速查表
```python
import os
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET 未设置")
```

### ✅ 检查点
- [ ] 为什么启动时 `if not JWT_SECRET: raise` 是好事不是 bug？
- [ ] `.env` 应该加入 `.gitignore` 吗？为什么？

---

## 📖 第五关：FastAPI 的自动验票机（Depends）

### 一句话
`Depends(get_current_user)` 就是**闸机自动验票机**：每个进接口的人必须先过这关，票不对直接拦下，你的业务代码完全不用管。

### 生活类比
你去健身房：
1. 刷卡进门（请求头带 `Authorization: Bearer <token>`）
2. 闸机自动读卡 → 查黑名单 → 验过期 → 验钢印（`jwt.decode`）
3. 闸机把会员信息贴在身上（返回 `{"id":1, "username":"john", "role":"USER"}`）
4. 教练（业务代码）直接看你身上的标签就知道你是谁

### 💻 你的项目里 [app/routers/auth.py:73-97](app/routers/auth.py)

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt, hashlib

security = HTTPBearer()   # 自动从请求头提取 Bearer Token

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    token = credentials.credentials

    # ① 查黑名单（不是先验签，先看有没有挂失）
    token_hash = hashlib.sha256(token.encode()).hexdigest()[:64]
    if db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first():
        # HTTPException 是 FastAPI 的异常类——主动抛出一个受控的 HTTP 错误（状态码 + detail）
        raise HTTPException(status_code=401, detail="Token 已被撤销，请重新登录")

    # ② 验签
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="门票已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的门票")

    # ③ 验过了，把身份信息贴在身上
    return {
        "id": int(payload["sub"]),
        "username": payload["username"],
        "role": payload["role"],
    }


# ========== 使用：一行保护任意路由 ==========
@app.get("/vip-room")
def enter_vip(user: dict = Depends(get_current_user)):
    return {"message": f"欢迎 VIP {user['username']}"}
```

### 🔍 逐步拆解
1. 前端请求头：`Authorization: Bearer <your-jwt>`
2. `HTTPBearer()` 自动提取 `eyJhbG...` → `credentials.credentials`
3. **先查黑名单** `token_hash`（不是先验签——挂失的票直接拦，连验签都不值得）
4. `jwt.decode` 验钢印
5. ✅ → 返回 user 字典注入业务函数，❌ → FastAPI 自动 401

> ⚠️ **设计要点**：为什么先查黑名单再验签？因为黑名单命中率高得多（用户主动登出），先做便宜的检查。而且黑名单用 SHA256 前 64 位哈希，不存完整 Token——即使黑名单表泄露，攻击者也反推不出原始 Token（SHA256 单向）。

### 📋 速查表
```python
security = HTTPBearer()

def get_current_user(creds = Depends(security), db = Depends(get_db)):
    # ① 查黑名单
    token_hash = hashlib.sha256(creds.credentials.encode()).hexdigest()[:64]
    if db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first():
        raise HTTPException(401, "Token 已撤销")
    # ② 验签
    payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    return {"id": int(payload["sub"]), "username": payload["username"], "role": payload["role"]}

# 保护路由
@app.get("/xxx")
def xxx(user = Depends(get_current_user)):
    ...
```

### ✅ 检查点
- [ ] `Depends(get_current_user)` 的执行顺序是什么？前端请求 → ？→ ？→ 业务代码
- [ ] 为什么先查黑名单再验签？
- [ ] `token_hash` 为什么用 SHA256 前 64 位而不是存完整 Token？

---

## 📖 第六关：角色授权 —— VIP 能进，普通会员不能进

### 一句话
认证通过后还要查"你能进哪间房"。这是**第二道闸机**。

### 💻 你的项目里 [app/routers/auth.py:101-112](app/routers/auth.py)

```python
def require_role(*allowed_roles: str):
    """
    角色守卫工厂 —— 用法:
        @app.get("/admin")
        def admin(user: dict = require_role("ADMIN")):
            ...
    """
    def checker(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"权限不足，需要角色: {allowed_roles}")
        return user
    return Depends(checker)


# ========== 使用 ==========
@app.delete("/articles/{id}")
def delete_article(user: dict = require_role("ADMIN", "EDITOR")):
    return {"message": f"{user['username']} 删除了文章"}

@app.get("/admin")
def admin_only(user: dict = require_role("ADMIN")):
    return {"message": f"欢迎管理员 {user['username']}", "stats": "机密数据"}
```

### 🔍 逐步拆解
1. `require_role("ADMIN")` 是一个**闭包工厂**——调用它返回 `Depends(checker)`
2. FastAPI 依赖链：`checker` → `get_current_user` → `HTTPBearer`，**从内到外**执行
3. 身份验证通过后，`checker` 看 `user["role"]` 是否在允许名单
4. 角色不对 → 403，业务代码**一行不执行**

### 📋 速查表
```python
def require_role(*roles):
    def checker(user = Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "权限不足")
        return user
    return Depends(checker)

# 仅管理员
Depends(require_role("ADMIN"))
# 多角色
Depends(require_role("ADMIN", "EDITOR"))
```

### ✅ 检查点
- [ ] `require_role` 为什么要用闭包（函数返回函数）而不是直接写死一个角色？
- [ ] 普通用户访问 `Depends(require_role("ADMIN"))` 保护的路由，返回什么 HTTP 状态码？

---

## 📖 第七关：注册 / 登录 / 登出完整流水线

### 生活类比——办健身卡全流程

- **注册**：填表 → 查重（这人办过了吗？）→ 密码绞肉 → 存库 → 发卡（JWT）
- **登录**：报手机号 → 查档案 → 对暗号 → 发卡
- **登出**：把卡挂失（Token 哈希加入黑名单）

### 💻 完整代码——你的项目 [app/routers/auth.py](app/routers/auth.py)

```python
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from models import User, RevokedToken

router = APIRouter(prefix="/auth", tags=["认证"])

# ========== Pydantic 请求体 ==========
class RegisterDto(BaseModel):
    username: str
    password: str

class LoginDto(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

# ========== 注册 ==========
@router.post("/register", response_model=TokenResponse)
def register(dto: RegisterDto, db: Session = Depends(get_db)):
    # ① 查重
    if db.query(User).filter(User.username == dto.username).first():
        raise HTTPException(status_code=400, detail="用户名已被注册")
    # ② 密码绞肉
    hashed = bcrypt.hashpw(dto.password.encode(), bcrypt.gensalt(rounds=10))
    # ③ 入库
    user = User(username=dto.username, password=hashed.decode(), role="USER")
    db.add(user); db.commit(); db.refresh(user)
    # ④ 发门票
    token = create_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, username=user.username, role=user.role)

# ========== 登录 ==========
@router.post("/login", response_model=TokenResponse)
def login(dto: LoginDto, db: Session = Depends(get_db)):
    # ① 查档案
    user = db.query(User).filter(User.username == dto.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    # ② 对暗号
    if not bcrypt.checkpw(dto.password.encode(), user.password.encode()):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    # ③ 发门票
    token = create_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, username=user.username, role=user.role)

# ========== 登出 ==========
@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    token_hash = _hash_token(token)   # SHA256前64位，不存完整Token

    # 解析过期时间放进黑名单，方便定时清理
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
                             options={"verify_exp": False})
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    except jwt.InvalidTokenError:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_HOURS)

    # 避免重复挂失
    if not db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first():
        revoked = RevokedToken(token_hash=token_hash, expires_at=expires_at)
        db.add(revoked); db.commit()

    return {"message": "已退出登录，Token 已失效"}
```

### 🔍 逐步拆解——注册
1. `RegisterDto` — Pydantic 自动校验 JSON body 必须有 `username` + `password`
2. 查重 — `db.query(User).filter(...).first()`，有结果就 400
3. `bcrypt.hashpw(...).decode()` — 二进制 → 字符串存库
4. `db.refresh(user)` — 拿到数据库自动生成的 `user.id`
5. `create_token(user.id, ...)` — 签发 JWT
6. `TokenResponse` — Pydantic 自动序列化为 JSON

### 🔍 逐步拆解——登出
1. 不依赖 `get_current_user`（过期 Token 也允许登出）
2. `options={"verify_exp": False}` — 跳过过期检查，只解析 payload 拿 `exp` 时间
3. `_hash_token(token)` — 只存 SHA256 前 64 位，不存完整 Token
4. 去重检查 — 同一个 Token 挂失两次不会报错

### 数据库表设计——你的项目 [models.py:17-35](models.py)

```python
class User(Base):
    """👤 用户（认证系统）"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(200), nullable=False)  # bcrypt 哈希值
    role = Column(String(20), default="USER")
    created_at = Column(DateTime, default=datetime.now)


class RevokedToken(Base):
    """🚫 Token 黑名单（挂失的 Token）"""
    __tablename__ = "revoked_tokens"
    id = Column(Integer, primary_key=True)
    token_hash = Column(String(64), unique=True, index=True)  # SHA256前64位，不存完整Token
    revoked_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # 自然过期时间，方便定时清理
```

> ⚠️ **为什么存 `token_hash` 而不是完整 Token？** 黑名单是安全敏感数据。即使数据库被脱库，攻击者也拿不到完整 Token（SHA256 不可逆），无法伪造请求。

### 📋 速查表
```python
# RegisterDto / LoginDto / TokenResponse
class RegisterDto(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

# 注册四步
user = User(username=dto.username, password=bcrypt.hashpw(dto.password.encode(), bcrypt.gensalt(rounds=10)).decode(), role="USER")
db.add(user); db.commit(); db.refresh(user)
token = create_token(user.id, user.username, user.role)

# 登录三步
user = db.query(User).filter(User.username == dto.username).first()
if not user or not bcrypt.checkpw(dto.password.encode(), user.password.encode()):
    raise HTTPException(401, "账号或密码错误")
token = create_token(user.id, user.username, user.role)

# 登出两步
token_hash = _hash_token(credentials.credentials)
db.add(RevokedToken(token_hash=token_hash, expires_at=...))
db.commit()
```

> ⚠️ **为什么登出用 `Depends(security)` 而不用 `Depends(get_current_user)`？** `get_current_user` 会先查黑名单再验签，对于已过期或需挂失的 Token 直接抛 401，根本走不到黑名单写入这一步。登出时只需要**提取 Token 字符串**（HTTPBearer 就能做到），然后无条件尝试加入黑名单——包括已过期的 Token（`verify_exp=False`）。

### ✅ 检查点
- [ ] 注册和登录的错误提示为什么都写"账号或密码错误"而不是分开写？
- [ ] 登出时为什么不需要 `Depends(get_current_user)`？
- [ ] `RevokedToken` 为什么存 `token_hash` 而不是完整 Token？

---

## 📖 第八关：JWT 的两个致命缺陷与补丁

### 缺陷 1：门票发出后没法"挂失"

**问题**：JWT 是无状态的——服务器只验钢印和日期，不记谁领了票。用户点"退出登录"，Token 在过期前依然能刷开门！

**补丁：黑名单（RevokedToken 表）**

验票前先查挂失名单，命中就直接拦：

```python
token_hash = _hash_token(credentials.credentials)
if db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first():
    raise HTTPException(status_code=401, detail="Token 已被撤销，请重新登录")
```

> 黑名单破坏了 JWT"无状态"的优雅，但换来了**可控的安全性**。生产环境建议用 Redis 存黑名单（自带 TTL 自动过期）。

---

### 缺陷 2：有效期太长不安全，太短体验差

**补丁：长短 Token 双卡制**（概念了解，暂不实现）

| 卡类型 | 有效期 | 服务器存不存 | 类比 |
|--------|--------|:---:|------|
| **Access Token**（门禁卡） | 15分钟~2小时 | ❌ 不存（纯无状态） | 刷一下就过，丢了只影响 15 分钟 |
| **Refresh Token**（换卡券） | 7~30天 | ✅ 必须存数据库 | 藏好，只在门禁卡过期时拿出来换新的 |

**流程**：
```
前端 ──Access Token──→ API（闸机秒过，无状态）
   ←── 401 过期 ──
前端 ──Refresh Token──→ /refresh（查档案）→ 新 Access Token
```

> 这是业界平衡安全与性能的最佳实践。本项目当前用单 Token + 黑名单方案，长短 Token 作为进阶升级方向。

### 📋 速查表
```python
# 黑名单验证（嵌入 get_current_user）
token_hash = hashlib.sha256(token.encode()).hexdigest()[:64]
if db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first():
    raise HTTPException(401, "Token 已撤销")

# 登出时加入黑名单
token_hash = _hash_token(token)
payload = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})
expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
db.add(RevokedToken(token_hash=token_hash, expires_at=expires_at))
```

| 对比 | 单 Token + 黑名单（当前） | 长短 Token（进阶） |
|------|--------------------------|---------------------|
| 复杂度 | ⭐⭐ | ⭐⭐⭐⭐ |
| 安全性 | 中（黑名单有状态开销） | 高 |
| 用户体验 | 过期需重新登录 | 无感刷新 |
| 适合场景 | 学习 / 内部工具 | 生产级应用 |

### ✅ 检查点
- [ ] 黑名单为什么说"破坏 JWT 无状态的优雅"？
- [ ] 长短 Token 里，为什么 Refresh Token 必须存数据库而 Access Token 不用？
- [ ] 如果只做单 Token 没有黑名单，用户点退出登录会怎样？

---

## 📖 第九关：Swagger 文档 & CORS & 异常兜底

> 本关不在原始文档中，是教学过程中补充的——每个 FastAPI 项目都需要。

### Swagger / OpenAPI 文档

FastAPI **自带**交互式 API 文档，只需启动后访问 `http://127.0.0.1:8000/docs`。

### 💻 你的项目 [main.py:49-57](main.py)

```python
app = FastAPI(
    title="Study Python API",
    description=DESCRIPTION,        # 显示在文档顶部的 Markdown
    version="0.1.0",
    openapi_tags=TAGS_METADATA,     # 按标签分组路由
    docs_url="/docs",               # Swagger UI
    redoc_url="/redoc",             # ReDoc 备选
)
```

### 💻 CORS 中间件 [main.py:60-66](main.py)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # 学习阶段允许所有来源，生产要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> **这是什么？** 浏览器默认禁止 `http://localhost:3000`（前端）请求 `http://localhost:8000`（后端）。CORS 中间件告诉浏览器："这个后端允许跨域，放行。"

### 💻 全局异常兜底 [main.py:68-76](main.py)

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """兜底异常处理：防止 500 裸奔返回给前端"""
    print(f"[异常] {request.method} {request.url.path} → {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {type(exc).__name__}"},
    )
```

> **为什么需要？** 没有这个处理器，后端崩溃时前端收到的是 HTML 堆栈页面。有了它，前端始终拿到 JSON `{"detail": "..."}`，可以统一处理。

### ✅ 检查点
- [ ] Swagger UI 在哪个 URL？没有 Swagger 的话前端怎么知道 API 接口长什么样？
- [ ] CORS 是干嘛的？为什么学习阶段用 `allow_origins=["*"]`，生产不能？
- [ ] 异常处理器的作用是什么？没有它的话，报 500 时前端收到什么？

---

## 📖 第十关：实战验证

> 这是教学过程中用 TestClient 跑通的 6 项核心测试，全部 PASS。

### 🧪 测试结果

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 1. 注册 → 200
r = client.post("/auth/register", json={"username": "testuser", "password": "test123"})
assert r.status_code == 200
assert "access_token" in r.json()

# 2. 登录 → 200
r = client.post("/auth/login", json={"username": "testuser", "password": "test123"})
token = r.json()["access_token"]
assert r.status_code == 200

# 3. /me → 200
r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
assert r.status_code == 200
assert r.json()["username"] == "testuser"

# 4. /admin（普通用户）→ 403
r = client.get("/auth/admin", headers={"Authorization": f"Bearer {token}"})
assert r.status_code == 403

# 5. 登出 → 200
r = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
assert r.status_code == 200

# 6. 登出后 /me → 401
r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
assert r.status_code == 401

# 7. 错误密码 → 401
r = client.post("/auth/login", json={"username": "testuser", "password": "wrong"})
assert r.status_code == 401

print("✅ 全部测试通过！")
```

### 🖥️ 用 curl 验证（不开 IDE 也能跑）

```bash
# 启动服务器
python main.py

# 新开终端：

# 1. 注册
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"john","password":"secret123"}'

# 2. 登录并保存 Token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"john","password":"secret123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 3. 查看身份
curl -s http://127.0.0.1:8000/auth/me -H "Authorization: Bearer $TOKEN"

# 4. 登出
curl -s -X POST http://127.0.0.1:8000/auth/logout -H "Authorization: Bearer $TOKEN"

# 5. 登出后重试（应该 401）
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  http://127.0.0.1:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

### ✅ 检查点
- [ ] 能不能不打开 Postman，只用 curl 跑通注册→登录→/me→登出→登出后 401 这条链路？

---

## 📋 终极速查表

### 密码哈希
```python
# 注册
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10))
# 登录
bcrypt.checkpw(password.encode(), stored_hash.encode())  # → True/False
```

### JWT 签发
```python
payload = {
    "sub": str(user_id), "role": role,
    "iat": datetime.now(timezone.utc),
    "exp": datetime.now(timezone.utc) + timedelta(hours=2)
}
token = jwt.encode(payload, SECRET, algorithm="HS256")
```

### JWT 验证 + 保护路由
```python
security = HTTPBearer()

def get_current_user(creds = Depends(security), db = Depends(get_db)):
    # ① 黑名单
    token_hash = hashlib.sha256(creds.credentials.encode()).hexdigest()[:64]
    if db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first():
        raise HTTPException(401, "Token 已撤销")
    # ② 验签
    payload = jwt.decode(creds.credentials, SECRET, algorithms=["HS256"])
    return {"id": int(payload["sub"]), "username": payload["username"], "role": payload["role"]}

@app.get("/xxx")
def xxx(user = Depends(get_current_user)):
    ...
```

### 角色守卫
```python
def require_role(*roles):
    def checker(user = Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "权限不足")
        return user
    return Depends(checker)

@app.delete("/xxx")
def xxx(user = require_role("ADMIN")):
    ...
```

### 请求头格式
```http
Authorization: Bearer <your-jwt>
```

### 环境变量配置
```python
import os
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise ValueError("JWT_SECRET 未设置")
```

---

## 🎮 常见陷阱表（贴在显示器上）

| 陷阱 | 后果 |
|------|------|
| JWT_SECRET 硬编码 | 源码泄露 = 全网 Token 可被伪造 |
| Payload 放密码/手机号 | Base64 可解码，信息裸奔 |
| 不设 Token 过期时间 | 一旦签发，永不过期 |
| 登录失败提示"密码错误" | 暴露账号存在性，方便撞库 |
| 只用 JWT 无黑名单实现登出 | 退出后 Token 依然可用 |
| .env 提交到 Git | 密钥永久留在版本历史里 |
| 生产环境依赖 .env 文件 | 文件权限配错 = 密钥裸奔 |
| 黑名单存完整 Token | 黑名单表泄露 = 所有挂失 Token 裸奔 |

---

## 🗺️ 完整思维导图

```
用户认证
├── 密码安全
│   ├── 绝不存明文
│   ├── bcrypt: 单向哈希 + Salt
│   └── 登录提示模糊化（防撞库）
├── JWT 令牌
│   ├── Header: 算法声明
│   ├── Payload: 用户ID/角色/过期时间（Base64裸奔，不放密码）
│   └── Signature: SECRET 防伪签名
├── 配置安全（十二因子）
│   ├── JWT_SECRET 走环境变量
│   ├── .env 不加 Git
│   └── 启动时强制校验（fail-fast）
├── FastAPI 实现
│   ├── /register: 查重 → bcrypt哈希 → 存库 → 发 Token
│   ├── /login: 查库 → bcrypt.checkpw → 发 Token
│   ├── /logout: Token 哈希加入黑名单
│   ├── Depends(get_current_user): HTTPBearer提取 → 查黑名单 → jwt.decode → 注入 user
│   └── require_role: 在 user.role 上做权限检查
├── 工程配置
│   ├── Swagger/OpenAPI: /docs 交互式文档
│   ├── CORS 中间件: 允许前端跨域
│   └── 全局异常处理器: 500 → JSON 不裸奔
└── 进阶策略
    ├── Token 黑名单: SHA256哈希方式解决撤销问题（RevokedToken 表）
    ├── 长短 Token: Access(短/无状态) + Refresh(长/存库)
    └── 黑名单清理: 定时删除已过期的 revoked token
```

---

## ✅ 汇总检查点

- [ ] 能用自己的话说出 401 和 403 的区别
- [ ] 能解释 bcrypt 的 Salt + rounds 是干嘛的
- [ ] 能画出 JWT 三段结构，知道 Payload 能被任何人解码
- [ ] 能写出 `Depends(get_current_user)` 保护 FastAPI 路由的代码
- [ ] 能解释为什么先查黑名单再验签
- [ ] 能写出 `require_role("ADMIN")` 角色守卫的代码
- [ ] 理解 JWT "无状态"的好处和"无法撤销"的坏处
- [ ] 知道长短 Token 里 Refresh Token 为什么必须服务端存储
- [ ] 知道 JWT_SECRET 为什么必须从环境变量读取，绝不能硬编码
- [ ] 能描述登出时黑名单（RevokedToken）的工作流程，为什么用 `token_hash` 不存完整 Token
- [ ] 知道 Swagger UI 地址和 CORS 的作用
- [ ] 能用 curl 完整跑通注册→登录→/me→登出→401 整条链路

---

## 📂 相关文件速查

| 文件 | 内容 |
|------|------|
| [app/routers/auth.py](../app/routers/auth.py) | 全部认证逻辑：5个接口 + 验票机 + 角色守卫 |
| [models.py](../models.py) | User 表（:17-25）+ RevokedToken 表（:28-35） |
| [main.py](../main.py) | Swagger 配置（:49-57）+ CORS（:60-66）+ 异常兜底（:68-76）+ 路由注册（:84） |
| [.env](../.env) | JWT_SECRET 环境变量 |
| Swagger UI | 启动后访问 http://127.0.0.1:8000/docs |
| [pyproject.toml](../pyproject.toml) | bcrypt + pyjwt 依赖 |

