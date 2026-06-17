# 芯墨·写作工坊

AI 驱动的长篇小说写作工具，支持从创意到正文的全流程创作。

## 直接使用（无需部署）

1. 到 [Releases](https://github.com/yourname/xinmo-writer/releases) 下载最新版 `芯墨写作工坊.zip`
2. 解压到任意目录
3. 双击 `芯墨写作工坊.exe` 即可使用

> 首次运行需在「设置」页面配置 API Key（支持 DeepSeek、OpenAI 等兼容 API）。

## 功能特性

- 🎯 **创作向导** — 一键生成小说设定（角色、世界观、故事线）
- 📚 **分卷大纲** — AI 规划全书分卷结构
- 📝 **整文细纲** — 逐卷生成章节细纲（冲突、爽点、钩子、伏笔）
- ✍️ **全书正文** — 逐章生成正文，流式输出，实时预览
- 🔖 **伏笔管理** — 自动追踪伏笔埋设与回收
- 🎭 **写手系统** — 多种写作风格可选
- 💻 **桌面版** — 双击即用，无需配置环境

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Element Plus + Vite |
| 后端 | FastAPI + SQLite |
| AI | OpenAI 兼容 API（DeepSeek 等） |
| 桌面 | PyWebView + PyInstaller |

## 配置

### config.json（exe 同级目录）

```json
{
  "port": 8077,
  "db_path": "data/novels.db"
}
```

- `port` — 后端服务端口（桌面版前后端同源，改端口不影响前端）
- `db_path` — 数据库路径（如为相对路径，基于 `_internal/` 目录）

修改后重启生效。开发模式下前端 Vite 代理自动读取该端口。

### 设置页面

- API Key / Base URL / 模型 — 在「设置」页面配置，存储在数据库中
- 写作风格 — 正文字数、标题字数、写作规则等

## 创作流程

1. **创作向导** — 输入创意 → 选择题材 → 选择书名 → 选择写手 → 生成设定
2. **角色体系** — 查看/编辑 AI 生成的角色设定
3. **分卷大纲** — AI 规划全书分卷 → 逐卷生成详细大纲
4. **整文细纲** — 逐卷生成章节细纲（冲突、爽点、钩子、伏笔）
5. **全书正文** — 逐章生成正文，支持流式预览

## 项目结构

```
xinmo-writer/
├── config.json              # 配置文件（打包后自动生成到 exe 同级）
├── README.md
├── .gitignore
├── xinmo_desktop.spec       # PyInstaller 打包配置
├── backend/                 # 后端源码
│   ├── main.py              # FastAPI 入口
│   ├── main_desktop.py      # 桌面版入口
│   ├── requirements.txt     # Python 依赖
│   ├── novel/               # 核心模块
│   │   ├── models.py        # 数据库模型
│   │   ├── db.py            # 数据库操作
│   │   ├── writer.py        # LLM 写作引擎
│   │   ├── prompts.py       # Prompt 模板
│   │   └── writers.py       # 写手配置
│   └── scripts/             # 工具脚本
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── router/          # 路由
│   │   └── api/             # API 封装
│   └── dist/                # 构建产物
└── data/                    # 数据库文件（自动创建，被 gitignore）
```

## 开发

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

## 打包

```bash
cd frontend && npm run build && cd ..
pyinstaller xinmo_desktop.spec --clean --noconfirm
```

输出在 `dist/芯墨写作工坊/`。

## License

MIT
