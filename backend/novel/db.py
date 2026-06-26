import json
from datetime import datetime
from .models import get_db


class NovelDB:
    """数据库操作层，所有 CRUD 集中在这里。"""

    # ─── Book ────────────────────────────────────────────────────────
    @staticmethod
    def create_book(title, genre="", brief="", author_intent="",
                    excitement_direction="", hook_type="", storylines="[]",
                    writing_config="{}", world_building="", foreshadowing="[]",
                    writer_id="", target_words=0):
        import uuid
        db = get_db()
        bid = uuid.uuid4().hex[:12]
        db.execute(
            "INSERT INTO books (id, title, genre, brief, author_intent, excitement_direction, hook_type, storylines, "
            "writing_config, world_building, foreshadowing, writer_id, target_words) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (bid, title, genre, brief, author_intent, excitement_direction, hook_type, storylines,
             writing_config, world_building, foreshadowing, writer_id, target_words),
        )
        db.commit()
        book = dict(db.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone())
        db.close()
        return book

    @staticmethod
    def list_books():
        db = get_db()
        rows = db.execute("SELECT * FROM books ORDER BY updated_at DESC").fetchall()
        books = []
        for r in rows:
            b = dict(r)
            ch = db.execute(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(word_count),0) as wc FROM chapters WHERE book_id=?",
                (b["id"],),
            ).fetchone()
            b["chapter_count"] = ch["cnt"]
            b["total_words"] = ch["wc"]
            books.append(b)
        db.close()
        return books

    @staticmethod
    def get_book(book_id):
        db = get_db()
        b = dict(db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone() or {})
        if not b:
            db.close()
            return None
        ch = db.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(word_count),0) as wc FROM chapters WHERE book_id=?",
            (book_id,),
        ).fetchone()
        b["chapter_count"] = ch["cnt"]
        b["total_words"] = ch["wc"]
        db.close()
        return b

    @staticmethod
    def update_book(book_id, **kwargs):
        allowed = {"title", "genre", "brief", "author_intent", "current_focus",
                   "excitement_direction", "hook_type", "storylines",
                   "writing_config", "world_building", "foreshadowing", "writer_id", "target_words",
                   "planned_volumes"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields:
            return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [book_id]
        db = get_db()
        db.execute(f"UPDATE books SET {sets} WHERE id=?", vals)
        db.commit()
        db.close()

    @staticmethod
    def delete_book(book_id):
        db = get_db()
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        db.close()

    # ─── Character ───────────────────────────────────────────────────
    @staticmethod
    def create_character(book_id, name, description="", background="", traits=None,
                         appearance="", relationships=None,
                         first_appearance_volume=1, first_appearance_desc="",
                         speech_style="", dialogue_sample="", emotion_profile=""):
        if traits is None: traits = []
        if relationships is None: relationships = []
        db = get_db()
        cur = db.execute(
            "INSERT INTO characters (book_id, name, description, background, traits, appearance, relationships, "
            "first_appearance_volume, first_appearance_desc, speech_style, dialogue_sample, emotion_profile) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (book_id, name, description, background, json.dumps(traits, ensure_ascii=False),
             appearance, json.dumps(relationships, ensure_ascii=False),
             first_appearance_volume, first_appearance_desc, speech_style, dialogue_sample, emotion_profile),
        )
        db.commit()
        c = dict(db.execute("SELECT * FROM characters WHERE id=?", (cur.lastrowid,)).fetchone())
        db.close()
        return c

    @staticmethod
    def list_characters(book_id):
        db = get_db()
        rows = db.execute("SELECT * FROM characters WHERE book_id=? ORDER BY created_at", (book_id,)).fetchall()
        db.close()
        result = []
        for r in rows:
            d = dict(r)
            d["traits"] = json.loads(d.get("traits", "[]"))
            d["relationships"] = json.loads(d.get("relationships", "[]"))
            result.append(d)
        return result

    @staticmethod
    def get_character(char_id):
        db = get_db()
        r = dict(db.execute("SELECT * FROM characters WHERE id=?", (char_id,)).fetchone() or {})
        db.close()
        if r:
            r["traits"] = json.loads(r.get("traits", "[]"))
            r["relationships"] = json.loads(r.get("relationships", "[]"))
        return r or None

    @staticmethod
    def update_character(char_id, **kwargs):
        allowed = {"name", "description", "background", "traits", "appearance", "relationships", "status",
                   "first_appearance_volume", "first_appearance_desc", "speech_style", "dialogue_sample", "emotion_profile"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields: return
        if "traits" in fields and isinstance(fields["traits"], list):
            fields["traits"] = json.dumps(fields["traits"], ensure_ascii=False)
        if "relationships" in fields and isinstance(fields["relationships"], list):
            fields["relationships"] = json.dumps(fields["relationships"], ensure_ascii=False)
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [char_id]
        db = get_db()
        db.execute(f"UPDATE characters SET {sets} WHERE id=?", vals)
        db.commit()
        db.close()

    @staticmethod
    def delete_character(char_id):
        db = get_db()
        db.execute("DELETE FROM characters WHERE id=?", (char_id,))
        db.commit()
        db.close()

    # ─── Volume ──────────────────────────────────────────────────────
    @staticmethod
    def create_volume(book_id, number, title, summary="", status="planned", chapter_count=0,
                      theme="", main_conflict="", turning_point="", character_arc="",
                      world_change="", foreshadowing_plan="", emotional_tone="", climax="",
                      subtitle="", chapter_start=0, chapter_end=0, key_nodes="[]",
                      emotion_arc="", characters_in_vol="[]", end_hook="", estimated_words=0):
        db = get_db()
        cur = db.execute(
            "INSERT INTO volumes (book_id, number, title, summary, status, chapter_count, "
            "theme, main_conflict, turning_point, character_arc, world_change, "
            "foreshadowing_plan, emotional_tone, climax, "
            "subtitle, chapter_start, chapter_end, key_nodes, "
            "emotion_arc, characters_in_vol, end_hook, estimated_words) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (book_id, number, title, summary, status, chapter_count,
             theme, main_conflict, turning_point, character_arc,
             world_change, foreshadowing_plan, emotional_tone, climax,
             subtitle, chapter_start, chapter_end, key_nodes,
             emotion_arc, characters_in_vol, end_hook, estimated_words),
        )
        db.commit()
        v = dict(db.execute("SELECT * FROM volumes WHERE id=?", (cur.lastrowid,)).fetchone())
        db.close()
        return v

    @staticmethod
    def list_volumes(book_id):
        db = get_db()
        rows = db.execute("SELECT * FROM volumes WHERE book_id=? ORDER BY number", (book_id,)).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_volume(vol_id):
        db = get_db()
        r = dict(db.execute("SELECT * FROM volumes WHERE id=?", (vol_id,)).fetchone() or {})
        db.close()
        return r or None

    @staticmethod
    def update_volume(vol_id, **kwargs):
        allowed = {"number", "title", "summary", "status", "chapter_count",
                   "theme", "main_conflict", "turning_point", "character_arc",
                   "world_change", "foreshadowing_plan", "emotional_tone", "climax",
                   "subtitle", "chapter_start", "chapter_end", "key_nodes",
                   "emotion_arc", "characters_in_vol", "end_hook", "estimated_words"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields: return
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [vol_id]
        db = get_db()
        db.execute(f"UPDATE volumes SET {sets} WHERE id=?", vals)
        db.commit()
        db.close()

    @staticmethod
    def delete_volume(vol_id):
        db = get_db()
        db.execute("DELETE FROM volumes WHERE id=?", (vol_id,))
        db.commit()
        db.close()

    # ─── Outline ─────────────────────────────────────────────────────
    @staticmethod
    def create_outline(book_id, chapter_number, title="", outline_content="",
                       volume_id=None, word_target=2000,
                       conflict="", excitement="", hook="",
                       storyline="", foreshadowing="", foreshadowing_payoff="",
                       pace_type="", emotion=""):
        db = get_db()
        cur = db.execute(
            "INSERT INTO outlines (book_id, volume_id, chapter_number, title, outline_content, word_target, "
            "conflict, excitement, hook, storyline, foreshadowing, foreshadowing_payoff, pace_type, emotion) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (book_id, volume_id, chapter_number, title, outline_content, word_target,
             conflict, excitement, hook, storyline, foreshadowing, foreshadowing_payoff, pace_type, emotion),
        )
        db.commit()
        o = dict(db.execute("SELECT * FROM outlines WHERE id=?", (cur.lastrowid,)).fetchone())
        db.close()
        return o

    @staticmethod
    def list_outlines(book_id, volume_id=None):
        db = get_db()
        if volume_id:
            rows = db.execute(
                "SELECT * FROM outlines WHERE book_id=? AND volume_id=? ORDER BY chapter_number",
                (book_id, volume_id),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM outlines WHERE book_id=? ORDER BY chapter_number", (book_id,)
            ).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_outline(outline_id):
        db = get_db()
        r = dict(db.execute("SELECT * FROM outlines WHERE id=?", (outline_id,)).fetchone() or {})
        db.close()
        return r or None

    @staticmethod
    def update_outline(outline_id, **kwargs):
        allowed = {"chapter_number", "title", "outline_content", "word_target", "status", "volume_id",
                    "conflict", "excitement", "hook", "storyline", "foreshadowing", "foreshadowing_payoff",
                    "pace_type"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields: return
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [outline_id]
        db = get_db()
        db.execute(f"UPDATE outlines SET {sets} WHERE id=?", vals)
        db.commit()
        db.close()

    @staticmethod
    def delete_outline(outline_id):
        db = get_db()
        db.execute("DELETE FROM outlines WHERE id=?", (outline_id,))
        db.commit()
        db.close()

    # ─── Chapter ─────────────────────────────────────────────────────
    @staticmethod
    def create_chapter(book_id, chapter_number, title="", outline_id=None,
                       content="", summary="", word_count=0, status="draft"):
        db = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = db.execute(
            "INSERT INTO chapters (book_id, chapter_number, title, outline_id, content, summary, word_count, status) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (book_id, chapter_number, title, outline_id, content, summary, word_count, status),
        )
        db.execute("UPDATE books SET updated_at=? WHERE id=?", (now, book_id))
        db.commit()
        ch = dict(db.execute("SELECT * FROM chapters WHERE id=?", (cur.lastrowid,)).fetchone())
        db.close()
        return ch

    @staticmethod
    def list_chapters(book_id):
        db = get_db()
        rows = db.execute(
            "SELECT c.*, o.title as outline_title FROM chapters c "
            "LEFT JOIN outlines o ON c.outline_id=o.id "
            "WHERE c.book_id=? ORDER BY c.chapter_number", (book_id,)
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_chapter(chapter_id):
        db = get_db()
        r = dict(db.execute(
            "SELECT c.*, o.title as outline_title, o.outline_content FROM chapters c "
            "LEFT JOIN outlines o ON c.outline_id=o.id WHERE c.id=?", (chapter_id,)
        ).fetchone() or {})
        db.close()
        return r or None

    @staticmethod
    def get_chapter_by_number(book_id, chapter_number):
        db = get_db()
        r = dict(db.execute(
            "SELECT * FROM chapters WHERE book_id=? AND chapter_number=?",
            (book_id, chapter_number),
        ).fetchone() or {})
        db.close()
        return r or None

    @staticmethod
    def update_chapter(chapter_id, **kwargs):
        allowed = {"title", "content", "summary", "word_count", "status"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields: return
        fields["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [chapter_id]
        db = get_db()
        db.execute(f"UPDATE chapters SET {sets} WHERE id=?", vals)
        db.execute("UPDATE books SET updated_at=? WHERE id=(SELECT book_id FROM chapters WHERE id=?)",
                   (fields["updated_at"], chapter_id))
        db.commit()
        db.close()

    @staticmethod
    def delete_chapter(chapter_id):
        db = get_db()
        db.execute("DELETE FROM chapters WHERE id=?", (chapter_id,))
        db.commit()
        db.close()

    # ─── Injection ───────────────────────────────────────────────────
    @staticmethod
    def create_injection(book_id, name, content, category="style", is_active=1):
        db = get_db()
        cur = db.execute(
            "INSERT INTO injections (book_id, name, content, category, is_active) VALUES (?,?,?,?,?)",
            (book_id, name, content, category, is_active),
        )
        db.commit()
        r = dict(db.execute("SELECT * FROM injections WHERE id=?", (cur.lastrowid,)).fetchone())
        db.close()
        return r

    @staticmethod
    def list_injections(book_id):
        db = get_db()
        rows = db.execute("SELECT * FROM injections WHERE book_id=? ORDER BY created_at", (book_id,)).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def update_injection(inj_id, **kwargs):
        allowed = {"name", "content", "category", "is_active"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields: return
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [inj_id]
        db = get_db()
        db.execute(f"UPDATE injections SET {sets} WHERE id=?", vals)
        db.commit()
        db.close()

    @staticmethod
    def delete_injection(inj_id):
        db = get_db()
        db.execute("DELETE FROM injections WHERE id=?", (inj_id,))
        db.commit()
        db.close()

    # ─── QC Rules ────────────────────────────────────────────────────
    @staticmethod
    def create_qc_rule(book_id, name, description="", check_content="", severity="warning", is_active=1):
        db = get_db()
        cur = db.execute(
            "INSERT INTO qc_rules (book_id, name, description, check_content, severity, is_active) "
            "VALUES (?,?,?,?,?,?)",
            (book_id, name, description, check_content, severity, is_active),
        )
        db.commit()
        r = dict(db.execute("SELECT * FROM qc_rules WHERE id=?", (cur.lastrowid,)).fetchone())
        db.close()
        return r

    @staticmethod
    def list_qc_rules(book_id):
        db = get_db()
        rows = db.execute("SELECT * FROM qc_rules WHERE book_id=? ORDER BY created_at", (book_id,)).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def update_qc_rule(rule_id, **kwargs):
        allowed = {"name", "description", "check_content", "severity", "is_active"}
        fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if not fields: return
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [rule_id]
        db = get_db()
        db.execute(f"UPDATE qc_rules SET {sets} WHERE id=?", vals)
        db.commit()
        db.close()

    @staticmethod
    def delete_qc_rule(rule_id):
        db = get_db()
        db.execute("DELETE FROM qc_rules WHERE id=?", (rule_id,))
        db.commit()
        db.close()

    # ─── Memory ──────────────────────────────────────────────────────
    @staticmethod
    def add_memory(book_id, chapter_number, fact, fact_type="plot", source="auto"):
        db = get_db()
        db.execute(
            "INSERT INTO memory (book_id, chapter_number, fact_type, fact, source) VALUES (?,?,?,?,?)",
            (book_id, chapter_number, fact_type, fact, source),
        )
        db.commit()
        db.close()

    @staticmethod
    def add_memories(book_id, chapter_number, facts):
        db = get_db()
        db.executemany(
            "INSERT INTO memory (book_id, chapter_number, fact_type, fact, source) VALUES (?,?,?,?,?)",
            [(book_id, chapter_number, ft, f, s) for ft, f, s in facts],
        )
        db.commit()
        db.close()

    @staticmethod
    def get_active_memories(book_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM memory WHERE book_id=? AND is_active=1 ORDER BY chapter_number DESC LIMIT 100",
            (book_id,),
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_chapter_summaries(book_id, limit=5):
        db = get_db()
        rows = db.execute(
            "SELECT chapter_number, title, summary FROM chapters "
            "WHERE book_id=? AND summary!='' ORDER BY chapter_number DESC LIMIT ?",
            (book_id, limit),
        ).fetchall()
        db.close()
        return [dict(r) for r in reversed(rows)]

    # ─── Character State ─────────────────────────────────────────────
    @staticmethod
    def upsert_character_state(book_id, character_id, name, location="", status="", last_chapter=0, time_note="", is_alive=1):
        db = get_db()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            """INSERT INTO character_states (book_id, character_id, name, location, status, last_chapter, time_note, is_alive, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(book_id, character_id) DO UPDATE SET
                 name=excluded.name, location=excluded.location, status=excluded.status,
                 last_chapter=excluded.last_chapter, time_note=excluded.time_note,
                 is_alive=excluded.is_alive, updated_at=excluded.updated_at""",
            (book_id, character_id, name, location, status, last_chapter, time_note, is_alive, now),
        )
        db.commit()
        db.close()

    @staticmethod
    def list_character_states(book_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM character_states WHERE book_id=? ORDER BY last_chapter DESC, name",
            (book_id,),
        ).fetchall()
        db.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_character_state(book_id, character_id):
        db = get_db()
        r = dict(db.execute(
            "SELECT * FROM character_states WHERE book_id=? AND character_id=?",
            (book_id, character_id),
        ).fetchone() or {})
        db.close()
        return r or None

    @staticmethod
    def delete_character_state(state_id):
        db = get_db()
        db.execute("DELETE FROM character_states WHERE id=?", (state_id,))
        db.commit()
        db.close()

    # ─── Config ──────────────────────────────────────────────────────
    @staticmethod
    def get_config(key, default=None):
        db = get_db()
        r = db.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        db.close()
        return r["value"] if r else default

    @staticmethod
    def set_config(key, value):
        db = get_db()
        db.execute(
            "INSERT INTO config (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=?",
            (key, value, value),
        )
        db.commit()
        db.close()

    @staticmethod
    def get_all_config():
        db = get_db()
        rows = db.execute("SELECT * FROM config").fetchall()
        db.close()
        return {r["key"]: r["value"] for r in rows}

    # ─── Writing Config (merged) ─────────────────────────────────────
    @staticmethod
    def get_default_writing_config():
        """获取全局默认写作风格配置"""
        raw = NovelDB.get_config("default_writing_config", "{}")
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def set_default_writing_config(config_dict):
        """保存全局默认写作风格配置"""
        NovelDB.set_config("default_writing_config", json.dumps(config_dict, ensure_ascii=False))

    @staticmethod
    def get_book_writing_config(book_id):
        """三级合并：全局默认 + 写手预设 + 单本覆盖。
        返回 (merged, book_config, default_config, is_custom)
        """
        from .writers import WRITERS_MAP

        default_cfg = NovelDB.get_default_writing_config()
        db = get_db()
        row = db.execute("SELECT writing_config, writer_id FROM books WHERE id=?", (book_id,)).fetchone()
        db.close()
        book_cfg = {}
        writer_id = ""
        is_custom = False
        if row:
            writer_id = row["writer_id"] or ""
            if row["writing_config"]:
                try:
                    book_cfg = json.loads(row["writing_config"])
                    is_custom = bool(book_cfg)
                except (json.JSONDecodeError, TypeError):
                    book_cfg = {}

        # 基础 = 全局默认
        result = dict(default_cfg)

        # 叠加写手配置（如果有）— 只有当 book_cfg 不含用户自定义时才叠加写手
        # 由于选写手时已将写手专属 config 存入 book_cfg，这里不需要再从 WRITERS_MAP 叠加
        # 直接将 book_cfg 作为写手+用户自定义的合并体叠加到默认上

        # 叠加 book_cfg（写手预设 / 用户自定义）
        if book_cfg:
            # 禁用词：追加
            if book_cfg.get("prohibited_words"):
                existing = result.get("prohibited_words", "")
                result["prohibited_words"] = (existing + "," + book_cfg["prohibited_words"]).strip(",") if existing else book_cfg["prohibited_words"]
            # 写作规则：追加
            if book_cfg.get("writing_rules"):
                existing = result.get("writing_rules", "")
                result["writing_rules"] = (existing + "\n" + book_cfg["writing_rules"]).strip() if existing else book_cfg["writing_rules"]
            # 行为锁：追加
            if book_cfg.get("behavior_locks"):
                existing = result.get("behavior_locks", "")
                result["behavior_locks"] = (existing + "\n" + book_cfg["behavior_locks"]).strip() if existing else book_cfg["behavior_locks"]
            # 高级设置：覆盖
            if book_cfg.get("advanced"):
                result["advanced"] = {**result.get("advanced", {}), **book_cfg["advanced"]}
            # 字数设置：覆盖
            for key in ["min_words", "max_words", "min_title_words", "max_title_words"]:
                if key in book_cfg and book_cfg[key] is not None:
                    result[key] = book_cfg[key]

        return result, book_cfg, default_cfg, is_custom
