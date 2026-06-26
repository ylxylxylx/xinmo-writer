import sqlite3
import json
import os
import sys
from datetime import datetime
import uuid

def _load_config():
    """加载配置文件"""
    # 打包后：config.json 在 exe 同级目录下
    if getattr(sys, 'frozen', False):
        config_path = os.path.join(os.path.dirname(sys.executable), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    # 打包后 / 开发：_internal/ 或 backend/
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # 开发模式：项目根目录
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

_config = _load_config()
_db_path = _config.get('db_path', 'data/novels.db')

if not os.path.isabs(_db_path):
    # 打包后：基于 _internal/ 目录
    if getattr(sys, 'frozen', False):
        DB_PATH = os.path.join(os.path.dirname(sys.executable), "_internal", _db_path)
    else:
        # 开发模式：基于项目根目录
        DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), _db_path)
else:
    DB_PATH = _db_path

# 确保数据目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init_db():
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS books (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            genre TEXT DEFAULT '',
            brief TEXT DEFAULT '',
            author_intent TEXT DEFAULT '',
            current_focus TEXT DEFAULT '',
            excitement_direction TEXT DEFAULT '',
            hook_type TEXT DEFAULT '',
            storylines TEXT DEFAULT '[]',
            writing_config TEXT DEFAULT '{}',
            world_building TEXT DEFAULT '',
            foreshadowing TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            background TEXT DEFAULT '',
            traits TEXT DEFAULT '[]',
            appearance TEXT DEFAULT '',
            relationships TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            first_appearance_volume INTEGER DEFAULT 1,
            first_appearance_desc TEXT DEFAULT '',
            speech_style TEXT DEFAULT '',
            dialogue_sample TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS volumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            number INTEGER NOT NULL,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            status TEXT DEFAULT 'planned',
            chapter_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            theme TEXT DEFAULT '',
            main_conflict TEXT DEFAULT '',
            turning_point TEXT DEFAULT '',
            character_arc TEXT DEFAULT '',
            world_change TEXT DEFAULT '',
            foreshadowing_plan TEXT DEFAULT '',
            emotional_tone TEXT DEFAULT '',
            climax TEXT DEFAULT '',
            subtitle TEXT DEFAULT '',
            chapter_start INTEGER DEFAULT 0,
            chapter_end INTEGER DEFAULT 0,
            key_nodes TEXT DEFAULT '[]',
            emotion_arc TEXT DEFAULT '',
            characters_in_vol TEXT DEFAULT '[]',
            end_hook TEXT DEFAULT '',
            estimated_words INTEGER DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS outlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            volume_id INTEGER,
            chapter_number INTEGER NOT NULL,
            title TEXT DEFAULT '',
            outline_content TEXT DEFAULT '',
            word_target INTEGER DEFAULT 2000,
            status TEXT DEFAULT 'planned',
            conflict TEXT DEFAULT '',
            excitement TEXT DEFAULT '',
            hook TEXT DEFAULT '',
            storyline TEXT DEFAULT '',
            foreshadowing TEXT DEFAULT '',
            foreshadowing_payoff TEXT DEFAULT '',
            pace_type TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (volume_id) REFERENCES volumes(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            chapter_number INTEGER NOT NULL,
            title TEXT DEFAULT '',
            outline_id INTEGER,
            content TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            word_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (outline_id) REFERENCES outlines(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS injections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'style',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS qc_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            check_content TEXT NOT NULL,
            severity TEXT DEFAULT 'warning',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            chapter_number INTEGER,
            fact_type TEXT,
            fact TEXT NOT NULL,
            source TEXT DEFAULT 'auto',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS character_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT NOT NULL,
            character_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            location TEXT DEFAULT '',
            status TEXT DEFAULT '',
            last_chapter INTEGER DEFAULT 0,
            time_note TEXT DEFAULT '',
            is_alive INTEGER DEFAULT 1,
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE,
            UNIQUE(book_id, character_id)
        );

        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    ''')
    # 为已有数据库添加新字段（兼容迁移）
    _migrations = [
        ("books", "excitement_direction", "TEXT DEFAULT ''"),
        ("books", "hook_type", "TEXT DEFAULT ''"),
        ("books", "storylines", "TEXT DEFAULT '[]'"),
        ("volumes", "chapter_count", "INTEGER DEFAULT 0"),
        ("outlines", "conflict", "TEXT DEFAULT ''"),
        ("outlines", "excitement", "TEXT DEFAULT ''"),
        ("outlines", "hook", "TEXT DEFAULT ''"),
        ("outlines", "storyline", "TEXT DEFAULT ''"),
        ("outlines", "foreshadowing", "TEXT DEFAULT ''"),
        ("outlines", "foreshadowing_payoff", "TEXT DEFAULT ''"),
        ("books", "writing_config", "TEXT DEFAULT '{}'"),
        ("books", "world_building", "TEXT DEFAULT ''"),
        ("books", "foreshadowing", "TEXT DEFAULT '[]'"),
        ("books", "writer_id", "TEXT DEFAULT ''"),
        ("books", "target_words", "INTEGER DEFAULT 0"),
        ("volumes", "theme", "TEXT DEFAULT ''"),
        ("volumes", "main_conflict", "TEXT DEFAULT ''"),
        ("volumes", "turning_point", "TEXT DEFAULT ''"),
        ("volumes", "character_arc", "TEXT DEFAULT ''"),
        ("volumes", "world_change", "TEXT DEFAULT ''"),
        ("volumes", "foreshadowing_plan", "TEXT DEFAULT ''"),
        ("volumes", "emotional_tone", "TEXT DEFAULT ''"),
        ("volumes", "climax", "TEXT DEFAULT ''"),
        ("volumes", "subtitle", "TEXT DEFAULT ''"),
        ("volumes", "chapter_start", "INTEGER DEFAULT 0"),
        ("volumes", "chapter_end", "INTEGER DEFAULT 0"),
        ("volumes", "key_nodes", "TEXT DEFAULT '[]'"),
        ("volumes", "emotion_arc", "TEXT DEFAULT ''"),
        ("volumes", "characters_in_vol", "TEXT DEFAULT '[]'"),
        ("volumes", "end_hook", "TEXT DEFAULT ''"),
        ("volumes", "estimated_words", "INTEGER DEFAULT 0"),
        ("books", "planned_volumes", "INTEGER DEFAULT 0"),
        ("characters", "first_appearance_volume", "INTEGER DEFAULT 1"),
        ("characters", "first_appearance_desc", "TEXT DEFAULT ''"),
        ("characters", "speech_style", "TEXT DEFAULT ''"),
        ("characters", "dialogue_sample", "TEXT DEFAULT ''"),
        ("outlines", "pace_type", "TEXT DEFAULT ''"),
        ("outlines", "emotion", "TEXT DEFAULT ''"),
        ("character_states", "is_alive", "INTEGER DEFAULT 1"),
        ("characters", "emotion_profile", "TEXT DEFAULT ''"),
    ]
    for table, column, col_type in _migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except sqlite3.OperationalError:
            pass  # 列已存在
    # 数据迁移：将 injections 中的世界观和写作风格迁移到 books 新字段
    _migrate_injections_to_new_fields(conn)

    # 插入全局默认写作风格配置（INSERT OR IGNORE 不覆盖用户自定义）
    default_writing_config = json.dumps({
        "min_words": 1900,
        "max_words": 2400,
        "min_title_words": 10,
        "max_title_words": 20,
        "prohibited_words": "仿佛,眼中闪过,嘴角勾起",
        "writing_rules": "这是小说不是剧本，对话后必须穿插动作/环境/心理描写\n段落不要过碎，相关动作合为一段\n不要长篇大论的环境描写，场景点到为止\n不要凭空造角色名，过场角色用身份称呼\n开篇不要绕，直接进戏",
        "behavior_locks": "主角/不圣母心泛滥，不无底线原谅伤害过自己的人\n反派/不突然降智，不强行洗白\n所有角色/不讲大道理不说教，对话中禁止长篇人生感悟\n所有角色/不突然知道不该知道的信息，不读心\nAI/禁止上帝视角评论人物行为，禁止跳出故事评判角色",
        "advanced": {
            "natural_dialogue": True,
            "no_useless_details": True,
            "max_env_sentences": 3,
            "max_inner_sentences": 3
        }
    }, ensure_ascii=False)
    conn.execute(
        "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
        ("default_writing_config", default_writing_config)
    )
    # 强制覆盖空占位符，确保已有数据库也能获得完整默认值
    conn.execute(
        "UPDATE config SET value=? WHERE key=? AND value=?",
        (default_writing_config, "default_writing_config", "{}")
    )
    conn.execute("DELETE FROM config WHERE key='default_writing_config' AND value='{}'")

    conn.commit()
    conn.close()


def _migrate_injections_to_new_fields(conn):
    """将旧 injections 表中的 world/style 类别数据迁移到 books 的新字段"""
    try:
        books = conn.execute("SELECT id FROM books").fetchall()
        for (book_id,) in books:
            # 迁移世界观：category='world' -> books.world_building
            world_rows = conn.execute(
                "SELECT content FROM injections WHERE book_id=? AND category='world' ORDER BY id",
                (book_id,)
            ).fetchall()
            if world_rows:
                book_row = conn.execute("SELECT world_building FROM books WHERE id=?", (book_id,)).fetchone()
                if book_row and not book_row[0]:
                    world_text = "\n\n".join(r[0] for r in world_rows)
                    conn.execute("UPDATE books SET world_building=? WHERE id=?", (world_text, book_id))

            # 迁移写作风格：category='style' -> books.writing_config.writing_rules
            style_rows = conn.execute(
                "SELECT content FROM injections WHERE book_id=? AND category='style' ORDER BY id",
                (book_id,)
            ).fetchall()
            if style_rows:
                import json
                book_row = conn.execute("SELECT writing_config FROM books WHERE id=?", (book_id,)).fetchone()
                if book_row:
                    try:
                        cfg = json.loads(book_row[0]) if book_row[0] else {}
                    except (json.JSONDecodeError, TypeError):
                        cfg = {}
                    if not cfg.get("writing_rules"):
                        rules = "\n".join(r[0] for r in style_rows)
                        cfg["writing_rules"] = rules
                        conn.execute(
                            "UPDATE books SET writing_config=? WHERE id=?",
                            (json.dumps(cfg, ensure_ascii=False), book_id)
                        )
    except Exception:
        pass  # 迁移失败不影响启动
