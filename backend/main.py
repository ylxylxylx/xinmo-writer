"""FastAPI 入口 — 芯墨式长篇小说写作工具"""

import json
import os
import sys
import traceback
from pathlib import Path
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from fastapi.templating import Jinja2Templates
import uvicorn
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent))
from novel.models import init_db
from novel.db import NovelDB, get_db
from novel.writer import NovelWriter
from novel.writers import WRITERS

# 初始化数据库
init_db()

app = FastAPI(title="芯墨·写作工坊", version="0.1.0")

BASE = Path(__file__).parent
PROJECT_ROOT = BASE.parent

writer = NovelWriter()


# ═══════════════════════════════════════════════════════════════════
# Wizard Service — 一句话创作向导
# ═══════════════════════════════════════════════════════════════════

class WizardService:
    def __init__(self):
        self._client = None
        self._model = None

    def _ensure_client(self):
        cfg = NovelDB.get_all_config()
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "https://api.deepseek.com")
        self._model = cfg.get("model", "deepseek-chat")
        if not api_key:
            raise ValueError("请先在设置中配置 API Key")
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def _chat(self, system_prompt, user_prompt, max_tokens=2048, temperature=0.8):
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        return raw

    def suggest_ideas(self):
        self._ensure_client()
        system = (
            "你是一个网文创意策划专家，擅长构思有吸引力的小说创意。\n"
            "请生成 5 个有吸引力的小说创意点子。\n"
            "每个创意用一段话描述（100-200字），包含：\n"
            "- 核心设定和世界观\n"
            "- 主角身份和特点\n"
            "- 核心冲突或悬念\n"
            "- 故事的爽点和看点\n"
            "要求：\n"
            "- 涵盖不同类型（末日、都市、古代、科幻、悬疑等，不要重复）\n"
            "- 要有新鲜感和商业吸引力\n"
            "- 严格输出 JSON 数组，每项是一个字符串\n"
            "不要输出其他内容，只输出 JSON。"
        )
        user = "请生成 5 个小说创意点子。"
        raw = self._chat(system, user, max_tokens=2048, temperature=0.9)
        candidates = json.loads(raw)
        if isinstance(candidates, list):
            return [str(c) for c in candidates]
        return []

    def suggest_genres(self, idea: str):
        self._ensure_client()
        system = (
            "你是一个网文策划专家，擅长为创意找到最合适的题材方向。\n"
            "用户会给你一句话创意，你需要给出 5-8 个题材方向候选。\n"
            "严格输出 JSON 数组，每个元素包含 name（题材名，4字以内）和 brief（一句话描述，20字以内）。\n"
            "不要输出其他内容，只输出 JSON。"
        )
        user = f"用户创意：{idea}"
        raw = self._chat(system, user, max_tokens=1024, temperature=0.9)
        candidates = json.loads(raw)
        if isinstance(candidates, list):
            return [{"name": c.get("name", ""), "brief": c.get("brief", "")} for c in candidates]
        return []

    def suggest_names(self, idea: str, genre: str):
        self._ensure_client()
        system = "你是网文书名策划专家。根据用户的创意和题材，生成8-10个爆款书名。"
        user = (
            f"创意：{idea}\n题材：{genre}\n\n"
            "【参考格式（必须模仿这种逗号分隔+反差感的风格）】\n"
            "输入：末日生存+房车+独狼变领袖\n"
            "输出：[\n"
            '  {"title": "末日房车，独狼的联盟之路", "brief": "末日降临，一辆破旧房车成为最后的庇护所。一个独狼从废墟中崛起，建立末日最强联盟。", "hook": "废墟崛起，逆袭称王"},\n'
            '  {"title": "开局一辆房车，我在末日建基地", "brief": "别人在末日挣扎求生，我开着系统升级的房车横扫丧尸，不知不觉成了末日之主。", "hook": "系统房车，碾压末日"},\n'
            '  {"title": "觉醒末日生存系统后，我成了末日霸主", "brief": "全球尸潮爆发，觉醒SSS级生存系统。当别人还在为一块面包拼命时，我已经建起了钢铁堡垒。", "hook": "SSS级天赋，碾压一切"}\n'
            "]\n\n"
            "【规则】\n"
            "1. 每个书名必须用逗号分隔两段，前半段点题，后半段制造反差或悬念\n"
            "2. 长度4-20字\n"
            "3. 不能平淡，要有「废墟崛起」「碾压末日」这种张力感\n\n"
            "现在请根据上面的参考格式，生成你的书名：\n"
            "严格输出JSON数组，每项含title/brief/hook三个字段，不要其他内容。"
        )
        raw = self._chat(system, user, max_tokens=2048, temperature=0.9)
        candidates = json.loads(raw)
        if isinstance(candidates, list):
            result = [
                {"title": c.get("title", ""), "brief": c.get("brief", ""), "hook": c.get("hook", "")}
                for c in candidates
            ]
        else:
            result = []

        # 后处理兜底：检查是否有逗号分隔的商业感书名
        has_comma = any("," in r["title"] or "，" in r["title"] or "：" in r["title"] or "、" in r["title"] for r in result)

        if not has_comma and result:
            # 根据用户创意和题材，用模板自动生成 3 个兜底书名
            genre_short = genre[:4] if genre else "末日"
            fallbacks = [
                {"title": f"{genre_short}，从独狼到联盟领袖", "brief": f"在{genre_short}世界中，主角从孤独求生者成长为联盟领袖", "hook": "独狼逆袭"},
                {"title": f"开局一辆破车，{genre_short}中建造移动城", "brief": f"凭借一辆破车，在{genre_short}世界中建造出移动城市", "hook": "破车建城"},
                {"title": f"{genre_short}，我的房车能无限升级", "brief": f"房车在{genre_short}中不断进化，成为最强生存堡垒", "hook": "无限升级"},
            ]
            result.extend(fallbacks)

        return result

    def generate_settings(self, idea: str, genre: str, title: str, brief: str, target_words: int, writer_style: str = ""):
        """三步生成设定：核心设定 → 故事架构 → 整合校验。"""
        self._ensure_client()

        # ── 第一步：核心设定（角色 + 世界观）──
        step1_system = (
            "你是一个资深网文世界观架构师。\n"
            "根据用户的创意，生成深入的角色设定和世界观。\n"
            "严格输出一个 JSON 对象，包含：\n"
            "- characters：角色数组，4-6 个角色，每个包含：\n"
            "  - name：角色名\n"
            "  - description：角色简介（150字以内，包含身份、性格、动机）\n"
            "  - background：背景故事（300字以内，详细的成长经历和关键事件）\n"
            "  - traits：性格特征（字符串数组，3-5个）\n"
            "  - appearance：外貌描写（100字以内，要有辨识度的细节）\n"
            "  - relationships：人际关系（数组，每项含 relation 和 target）\n"
            "- world_setting：世界观设定（800字以内，必须用【xxx】标记分段，例如：\n"
            "  【地理环境】描述世界的地理特征...\n"
            "  【势力格局】描述主要势力和关系...\n"
            "  【核心规则】描述世界运行的特殊规则...\n"
            "  【历史背景】描述重要的历史事件...\n"
            "  根据题材选择合适的分段标题，不要局限于以上示例）\n"
            "不要输出其他内容，只输出 JSON。"
        )
        step1_user = f"创意：{idea}\n题材：{genre}\n书名：{title}\n简介：{brief}"
        if writer_style:
            step1_user += f"\n写手风格：{writer_style}"

        raw1 = self._chat(step1_system, step1_user, max_tokens=8192, temperature=0.7)
        step1 = json.loads(raw1)

        # ── 第二步：故事架构（故事线 + 爽点 + 钩子）──
        chars_desc = "\n".join(
            f"- {c['name']}：{c.get('description', '')}" for c in step1.get("characters", [])
        )
        world_desc = step1.get("world_setting", "")

        step2_system = (
            "你是一个资深网文策划专家。\n"
            "根据已有的角色和世界观，设计故事架构。\n"
            "严格输出一个 JSON 对象，包含：\n"
            "- storylines：故事线数组，每个包含 name（名称）、type（main/side）、"
            "  description（200字以内，详细描述故事走向和关键转折）\n"
            "- excitement_direction：爽点方向（200字以内，描述核心爽感来源和类型）\n"
            "- hook_type：钩子策略（200字以内，描述断章钩子的设计方法）\n"
            "- hooks：爽点/钩子数组（3-5个具体场景，每个 50 字以内）\n"
            "- writing_style：写作风格指令（100字以内）\n"
            "故事线之间要有递进关系，不能互相矛盾。\n"
            "不要输出其他内容，只输出 JSON。"
        )
        step2_user = (
            f"创意：{idea}\n题材：{genre}\n书名：{title}\n简介：{brief}\n\n"
            f"角色：\n{chars_desc}\n\n"
            f"世界观：\n{world_desc}"
        )

        raw2 = self._chat(step2_system, step2_user, max_tokens=4096, temperature=0.8)
        step2 = json.loads(raw2)

        # ── 第三步：整合校验 ──
        step3_system = (
            "你是一个资深网文策划总监。\n"
            "根据已有的角色、世界观和故事架构，生成创作意图，并检查一致性。\n"
            "严格输出一个 JSON 对象，包含：\n"
            "- author_intent：创作意图（200字以内，描述本书的核心立意、目标读者、情感基调）\n"
            "- consistency_check：一致性检查结果（字符串，简述是否有矛盾，如有则说明如何修正）\n"
            "不要输出其他内容，只输出 JSON。"
        )
        step3_user = (
            f"创意：{idea}\n题材：{genre}\n书名：{title}\n简介：{brief}\n\n"
            f"角色设定：{json.dumps(step1.get('characters', []), ensure_ascii=False)}\n\n"
            f"世界观：{world_desc}\n\n"
            f"故事线：{json.dumps(step2.get('storylines', []), ensure_ascii=False)}\n\n"
            f"爽点方向：{step2.get('excitement_direction', '')}\n\n"
            f"钩子策略：{step2.get('hook_type', '')}"
        )

        raw3 = self._chat(step3_system, step3_user, max_tokens=2048, temperature=0.3)
        step3 = json.loads(raw3)

        # ── 合并结果 ──
        return {
            "title": title,
            "genre": genre,
            "brief": brief,
            "author_intent": step3.get("author_intent", ""),
            "characters": step1.get("characters", []),
            "world_setting": step1.get("world_setting", ""),
            "writing_style": step2.get("writing_style", ""),
            "hooks": step2.get("hooks", []),
            "excitement_direction": step2.get("excitement_direction", ""),
            "hook_type": step2.get("hook_type", ""),
            "storylines": step2.get("storylines", []),
        }


def clean_key_nodes(nodes):
    """清理关键节点格式，去掉序号/符号前缀，统一为纯文本数组。"""
    if not isinstance(nodes, list):
        return nodes
    import re
    cleaned = []
    for n in nodes:
        if not isinstance(n, str):
            n = str(n)
        # 去掉所有已有前缀
        s = re.sub(r'^[\s]*[•\-–—]\s*', '', n)
        s = re.sub(r'^[\s]*[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', s)
        s = re.sub(r'^[\s]*[（\(][一二三四五六七八九十\d]+[）\)]\s*', '', s)
        s = re.sub(r'^[\s]*[一二三四五六七八九十]+[、.．]\s*', '', s)
        s = re.sub(r'^[\s]*\d+[、.．\s]\s*', '', s)
        s = s.strip()
        if s:
            cleaned.append(s)
    return cleaned


def clean_text_list(text):
    """清理文本中的列表格式，统一为圈数字前缀。处理字符串中的 •、1.、① 等格式。"""
    if not text or not isinstance(text, str):
        return text
    import re
    circled = "①②③④⑤⑥⑦⑧⑨⑩"

    # 按行分割
    lines = text.split('\n')
    non_empty = [l.strip() for l in lines if l.strip()]

    # 如果只有一行且没有换行，尝试按句号/分号分割
    if len(non_empty) <= 1 and len(text) > 50:
        # 尝试按句号、分号、逗号分割成多个条目
        items = re.split(r'[。；;]\s*', text)
        items = [i.strip() for i in items if i.strip() and len(i.strip()) > 5]
        if len(items) > 1:
            result = []
            for i, item in enumerate(items):
                prefix = circled[i] if i < len(circled) else f"({i+1})"
                result.append(f"{prefix}{item}")
            return '\n'.join(result)

    result = []
    counter = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append(line)
            continue

        # 去掉已有前缀
        cleaned = stripped
        cleaned = re.sub(r'^[\s]*[•\-–—]\s*', '', cleaned)
        cleaned = re.sub(r'^[\s]*[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', cleaned)
        cleaned = re.sub(r'^[\s]*[（\(][一二三四五六七八九十\d]+[）\)]\s*', '', cleaned)
        cleaned = re.sub(r'^[\s]*[一二三四五六七八九十]+[、.．]\s*', '', cleaned)
        cleaned = re.sub(r'^[\s]*\d+[、.．\s]\s*', '', cleaned)
        cleaned = cleaned.strip()

        # 如果清理后内容变了，说明原来是列表项
        if cleaned != stripped.lstrip() and cleaned:
            prefix = circled[counter] if counter < len(circled) else f"({counter+1})"
            result.append(f"{prefix}{cleaned}")
            counter += 1
        else:
            # 检查是否以数字或符号开头
            if re.match(r'^[•\-–—①②③④⑤⑥⑦⑧⑨⑩\d一二三四五六七八九十（\(]', stripped):
                prefix = circled[counter] if counter < len(circled) else f"({counter+1})"
                result.append(f"{prefix}{cleaned}")
                counter += 1
            elif len(non_empty) > 1 and stripped:
                # 多行文本中，非空行都当作列表项
                prefix = circled[counter] if counter < len(circled) else f"({counter+1})"
                result.append(f"{prefix}{cleaned}")
                counter += 1
            else:
                result.append(line)

    return '\n'.join(result)


wizard = WizardService()



# API 路由
# ═══════════════════════════════════════════════════════════════════

# ── Book API ──

@app.post("/api/books")
async def api_create_book(
    title: str = Form(...),
    genre: str = Form(""),
    brief: str = Form(""),
    author_intent: str = Form(""),
    writer_id: str = Form(""),
):
    if not writer_id:
        writer_id = NovelDB.get_config("default_writer_id", "")
    book = NovelDB.create_book(title, genre, brief, author_intent, writer_id=writer_id)
    if writer_id:
        _apply_writer_to_book(book["id"], writer_id)
    return JSONResponse(book)

@app.get("/api/books/{book_id}/volumes")
async def api_list_volumes(book_id: str):
    return JSONResponse(NovelDB.list_volumes(book_id))

@app.get("/api/books/{book_id}/outlines")
async def api_list_outlines(book_id: str):
    return JSONResponse(NovelDB.list_outlines(book_id))

@app.get("/api/books/{book_id}/chapters")
async def api_list_chapters(book_id: str):
    return JSONResponse(NovelDB.list_chapters(book_id))

@app.get("/api/books/{book_id}/chapters/{chapter_id}")
async def api_get_chapter(book_id: str, chapter_id: int):
    ch = NovelDB.get_chapter(chapter_id)
    if not ch:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(ch)

@app.get("/api/books/{book_id}/injections")
async def api_list_injections(book_id: str):
    return JSONResponse(NovelDB.list_injections(book_id))

# QC质检API已禁用（写作风格重构后移除，db方法保留）
# @app.get("/api/books/{book_id}/rules")
# async def api_list_rules(book_id: str):
#     return JSONResponse(NovelDB.list_qc_rules(book_id))


@app.post("/api/books/{book_id}/update")
async def api_update_book(book_id: str, title: str = Form(""), genre: str = Form(""),
                           brief: str = Form(""), author_intent: str = Form(""),
                           current_focus: str = Form(""),
                           excitement_direction: str = Form(""), hook_type: str = Form(""),
                           storylines: str = Form(""),
                           world_building: str = Form(None),
                           foreshadowing: str = Form(None),
                           writer_id: str = Form(None)):
    kwargs = dict(title=title, genre=genre, brief=brief,
                  author_intent=author_intent, current_focus=current_focus,
                  excitement_direction=excitement_direction, hook_type=hook_type)
    if storylines:
        kwargs["storylines"] = storylines
    if world_building is not None:
        kwargs["world_building"] = world_building
    if foreshadowing is not None:
        kwargs["foreshadowing"] = foreshadowing
    if writer_id is not None:
        kwargs["writer_id"] = writer_id
    NovelDB.update_book(book_id, **kwargs)
    return JSONResponse({"ok": True})

@app.get("/api/config")
async def api_get_config():
    return JSONResponse(NovelDB.get_all_config())

@app.get("/api/health")
async def api_health():
    return JSONResponse({"status": "ok", "name": "芯墨·写作工坊"})
@app.post("/api/books/{book_id}/delete")
async def api_delete_book(book_id: str):
    NovelDB.delete_book(book_id)
    return JSONResponse({"ok": True})



# ── Character API ──

@app.get("/api/books")
async def api_list_books():
    return JSONResponse(NovelDB.list_books())

@app.get("/api/books/{book_id}")
async def api_get_book(book_id: str):
    book = NovelDB.get_book(book_id)
    if not book:
        return JSONResponse({"error": "not found"}, status_code=404)
    db = get_db()
    book["character_count"] = db.execute("SELECT COUNT(*) FROM characters WHERE book_id=?", (book_id,)).fetchone()[0]
    book["volume_count"] = db.execute("SELECT COUNT(*) FROM volumes WHERE book_id=?", (book_id,)).fetchone()[0]
    book["outline_count"] = db.execute("SELECT COUNT(*) FROM outlines WHERE book_id=?", (book_id,)).fetchone()[0]
    db.close()
    book["characters"] = NovelDB.list_characters(book_id)
    book["volumes"] = NovelDB.list_volumes(book_id)
    book["outlines"] = NovelDB.list_outlines(book_id)
    book["chapters"] = NovelDB.list_chapters(book_id)
    book["injections"] = NovelDB.list_injections(book_id)
    book["qc_rules"] = NovelDB.list_qc_rules(book_id)
    # 解析 foreshadowing JSON
    try:
        book["foreshadowing_parsed"] = json.loads(book.get("foreshadowing", "[]"))
    except (json.JSONDecodeError, TypeError):
        book["foreshadowing_parsed"] = []
    return JSONResponse(book)


@app.get("/api/books/{book_id}/characters")
async def api_list_characters(book_id: str):
    chars = NovelDB.list_characters(book_id)
    return JSONResponse(chars)


@app.post("/api/books/{book_id}/characters")
async def api_create_character(
    book_id: str,
    name: str = Form(...),
    description: str = Form(""),
    background: str = Form(""),
    traits: str = Form("[]"),
    appearance: str = Form(""),
    relationships: str = Form("[]"),
):
    try:
        traits_list = json.loads(traits)
        rels_list = json.loads(relationships)
    except json.JSONDecodeError:
        traits_list = []
        rels_list = []
    c = NovelDB.create_character(book_id, name, description, background,
                                  traits_list, appearance, rels_list)
    return JSONResponse(c)


@app.post("/api/characters/{char_id}/update")
async def api_update_character(char_id: int, name: str = Form(""),
                                description: str = Form(""), background: str = Form(""),
                                traits: str = Form(None), appearance: str = Form(""),
                                relationships: str = Form(None)):
    kwargs = {"name": name, "description": description, "background": background, "appearance": appearance}
    if traits is not None:
        try:
            kwargs["traits"] = json.loads(traits)
        except json.JSONDecodeError:
            pass
    if relationships is not None:
        try:
            kwargs["relationships"] = json.loads(relationships)
        except json.JSONDecodeError:
            pass
    NovelDB.update_character(char_id, **kwargs)
    return JSONResponse({"ok": True})



@app.post("/api/characters/{char_id}/delete")
async def api_delete_character(char_id: int):
    NovelDB.delete_character(char_id)
    return JSONResponse({"ok": True})



# ── Volume API ──

@app.post("/api/books/{book_id}/volumes")
async def api_create_volume(book_id: str, number: int = Form(...),
                             title: str = Form(...), summary: str = Form(""),
                             status: str = Form("planned"),
                             chapter_count: int = Form(0),
                             theme: str = Form(""), main_conflict: str = Form(""),
                             turning_point: str = Form(""), character_arc: str = Form(""),
                             world_change: str = Form(""), foreshadowing_plan: str = Form(""),
                             emotional_tone: str = Form(""), climax: str = Form(""),
                             subtitle: str = Form(""), chapter_start: int = Form(0),
                             chapter_end: int = Form(0), key_nodes: str = Form("[]"),
                             emotion_arc: str = Form(""), characters_in_vol: str = Form("[]"),
                             end_hook: str = Form(""), estimated_words: int = Form(0)):
    v = NovelDB.create_volume(book_id, number, title, summary, status, chapter_count,
                              theme, main_conflict, turning_point, character_arc,
                              world_change, foreshadowing_plan, emotional_tone, climax,
                              subtitle, chapter_start, chapter_end, key_nodes,
                              emotion_arc, characters_in_vol, end_hook, estimated_words)
    return JSONResponse(v)


@app.post("/api/volumes/{vol_id}/update")
async def api_update_volume(vol_id: int, number: int = Form(None),
                             title: str = Form(None), summary: str = Form(None),
                             status: str = Form(None),
                             chapter_count: int = Form(None),
                             theme: str = Form(None), main_conflict: str = Form(None),
                             turning_point: str = Form(None), character_arc: str = Form(None),
                             world_change: str = Form(None), foreshadowing_plan: str = Form(None),
                             emotional_tone: str = Form(None), climax: str = Form(None),
                             subtitle: str = Form(None), chapter_start: int = Form(None),
                             chapter_end: int = Form(None), key_nodes: str = Form(None),
                             emotion_arc: str = Form(None), characters_in_vol: str = Form(None),
                             end_hook: str = Form(None), estimated_words: int = Form(None)):
    kwargs = {}
    if number is not None: kwargs["number"] = number
    if title is not None: kwargs["title"] = title
    if summary is not None: kwargs["summary"] = summary
    if status is not None: kwargs["status"] = status
    if chapter_count is not None: kwargs["chapter_count"] = chapter_count
    if theme is not None: kwargs["theme"] = theme
    if main_conflict is not None: kwargs["main_conflict"] = main_conflict
    if turning_point is not None: kwargs["turning_point"] = turning_point
    if character_arc is not None: kwargs["character_arc"] = character_arc
    if world_change is not None: kwargs["world_change"] = world_change
    if foreshadowing_plan is not None: kwargs["foreshadowing_plan"] = foreshadowing_plan
    if emotional_tone is not None: kwargs["emotional_tone"] = emotional_tone
    if climax is not None: kwargs["climax"] = climax
    if subtitle is not None: kwargs["subtitle"] = subtitle
    if chapter_start is not None: kwargs["chapter_start"] = chapter_start
    if chapter_end is not None: kwargs["chapter_end"] = chapter_end
    if key_nodes is not None: kwargs["key_nodes"] = key_nodes
    if emotion_arc is not None: kwargs["emotion_arc"] = emotion_arc
    if characters_in_vol is not None: kwargs["characters_in_vol"] = characters_in_vol
    if end_hook is not None: kwargs["end_hook"] = end_hook
    if estimated_words is not None: kwargs["estimated_words"] = estimated_words
    NovelDB.update_volume(vol_id, **kwargs)
    return JSONResponse({"ok": True})



@app.post("/api/volumes/{vol_id}/delete")
async def api_delete_volume(vol_id: int):
    NovelDB.delete_volume(vol_id)
    return JSONResponse({"ok": True})


@app.post("/api/volumes/{vol_id}/generate-outlines")
async def api_generate_volume_outlines(vol_id: int, start_chapter: int = Form(0), batch_size: int = Form(5)):
    """为分卷生成章节细纲。start_chapter=0 表示从下一个未生成的章节开始，batch_size 默认 5。"""
    vol = NovelDB.get_volume(vol_id)
    if not vol:
        return JSONResponse({"error": "分卷不存在"}, status_code=404)
    book_id = vol["book_id"]
    book = NovelDB.get_book(book_id)
    characters = NovelDB.list_characters(book_id)
    merged_cfg, _, _, _ = NovelDB.get_book_writing_config(book_id)
    storylines_raw = book.get("storylines", "[]")
    try:
        storylines = json.loads(storylines_raw) if isinstance(storylines_raw, str) else storylines_raw
    except Exception:
        storylines = []
    chapter_count = vol.get("chapter_count", 0) or 0
    if chapter_count < 1:
        chapter_count = 20

    # 计算本卷已有的细纲
    existing_outlines = NovelDB.list_outlines(book_id, volume_id=vol_id)
    existing_nums = {o["chapter_number"] for o in existing_outlines}
    vol_chapter_start = vol.get("chapter_start", 0) or 1

    # 确定本次生成的起始章节号
    if start_chapter > 0:
        actual_start = start_chapter
    else:
        # 从本卷范围内的第一个未生成章节开始
        actual_start = vol_chapter_start
        for num in range(vol_chapter_start, vol_chapter_start + chapter_count):
            if num not in existing_nums:
                actual_start = num
                break
        else:
            return JSONResponse({"error": "该卷所有章节细纲已生成完毕", "done": True}, status_code=200)

    # 计算本次要生成的章节范围
    actual_end = min(actual_start + batch_size, vol_chapter_start + chapter_count)
    if actual_start >= vol_chapter_start + chapter_count:
        return JSONResponse({"error": "该卷所有章节细纲已生成完毕", "done": True}, status_code=200)

    gen_count = actual_end - actual_start
    # 已有细纲上下文
    existing_context = ""
    if existing_outlines:
        ctx_lines = []
        for o in sorted(existing_outlines, key=lambda x: x["chapter_number"])[-5:]:
            ctx_lines.append(f"第{o['chapter_number']}章「{o.get('title','')}」：{o.get('outline_content','')[:80]}")
        existing_context = "\n已有细纲（最近几章）：\n" + "\n".join(ctx_lines)

    char_desc = "\n".join(f"- {c['name']}：{c['description']}" for c in characters) or "暂无"
    cfg_desc = merged_cfg.get("writing_rules", "") or "暂无"
    sl_desc = "\n".join(f"- {s.get('name','')}（{s.get('type','')}）：{s.get('description','')}" for s in storylines) or "暂无"

    # 从写作风格配置读取字数设置
    min_title = merged_cfg.get("min_title_words", 10)
    max_title = merged_cfg.get("max_title_words", 20)
    min_words = merged_cfg.get("min_words", 2000)
    max_words = merged_cfg.get("max_words", 4000)

    system = (
        "你是一个资深网文大纲策划师。\n"
        "根据给定的小说信息、分卷摘要、角色、写作风格和故事线，为该分卷生成详细章节大纲。\n"
        "严格输出一个 JSON 数组，每个元素代表一个章节，包含以下字段：\n"
        "- chapter_number：章节序号（整数）\n"
        f"- title：章节标题（{min_title}-{max_title}字，要有吸引力，能概括本章核心冲突或悬念）\n"
        "- outline_content：详细大纲（150字以内，描述本章核心场景、情节转折、人物行动）\n"
        f"- word_target：目标字数（整数，默认{(min_words + max_words) // 2}）\n"
        "- conflict：核心冲突（50字以内）\n"
        "- excitement：爽点设计（50字以内）\n"
        "- hook：章末钩子/悬念（50字以内）\n"
        "- storyline：推进的故事线（50字以内）\n"
        "- foreshadowing：埋下的伏笔（50字以内）\n"
        "- foreshadowing_payoff：回收的伏笔（50字以内，可为空）\n"
        f"本次需要生成第{actual_start}章到第{actual_end - 1}章，共 {gen_count} 个章节。\n"
        f"chapter_number 必须从 {actual_start} 开始递增。\n"
        "不要输出其他内容，只输出 JSON。"
    )
    user = (
        f"书名：{book.get('title','')}\n"
        f"题材：{book.get('genre','')}\n"
        f"简介：{book.get('brief','')}\n"
        f"爽点方向：{book.get('excitement_direction','')}\n"
        f"钩子类型：{book.get('hook_type','')}\n\n"
        f"分卷编号：第{vol.get('number','')}卷\n"
        f"分卷名：{vol.get('title','')}\n"
        f"分卷摘要：{vol.get('summary','')}\n"
        f"本卷总章节数：{chapter_count}\n"
        f"核心主题：{vol.get('theme','')}\n"
        f"主要冲突：{vol.get('main_conflict','')}\n"
        f"关键转折：{vol.get('turning_point','')}\n"
        f"情绪弧线：{vol.get('emotion_arc','')}\n"
        f"卷尾钩子：{vol.get('end_hook','')}\n"
        f"角色弧线：{vol.get('character_arc','')}\n"
        f"世界观变化：{vol.get('world_change','')}\n"
        f"伏笔规划：{vol.get('foreshadowing_plan','')}\n"
        f"关键节点：{vol.get('key_nodes','')}\n\n"
        f"角色：\n{char_desc}\n\n"
        f"写作风格：\n{cfg_desc}\n\n"
        f"故事线：\n{sl_desc}"
        f"{existing_context}"
    )
    try:
        wizard._ensure_client()
        raw = wizard._chat(system, user, max_tokens=4096, temperature=0.7)
        chapters = json.loads(raw)
        if not isinstance(chapters, list):
            return JSONResponse({"error": "LLM 返回格式错误"}, status_code=500)
        # 不删除已有细纲，只追加新的
        created = []
        for i, ch in enumerate(chapters):
            ch_num = ch.get("chapter_number", actual_start + i)
            # 跳过已有细纲的章节
            if ch_num in existing_nums:
                continue
            o = NovelDB.create_outline(
                book_id=book_id,
                chapter_number=ch_num,
                title=ch.get("title", ""),
                outline_content=ch.get("outline_content", ""),
                volume_id=vol_id,
                word_target=ch.get("word_target", 2000),
                conflict=ch.get("conflict", ""),
                excitement=ch.get("excitement", ""),
                hook=ch.get("hook", ""),
                storyline=ch.get("storyline", ""),
                foreshadowing=ch.get("foreshadowing", ""),
                foreshadowing_payoff=ch.get("foreshadowing_payoff", ""),
            )
            created.append(o)
        total_in_vol = len(existing_outlines) + len(created)
        remaining = max(0, chapter_count - total_in_vol)
        done = remaining == 0
        return JSONResponse({
            "outlines": created, "count": len(created),
            "total_in_vol": total_in_vol, "remaining": remaining, "done": done
        })
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        return JSONResponse({"error": f"生成失败: {str(e)}"}, status_code=500)


@app.post("/api/books/{book_id}/plan-volumes")
async def api_plan_volumes(book_id: str):
    """规划阶段：根据目标字数规划全书分卷结构，创建所有卷的占位记录。"""
    book = NovelDB.get_book(book_id)
    if not book:
        return JSONResponse({"error": "作品不存在"}, status_code=404)

    characters = NovelDB.list_characters(book_id)
    foreshadowing = []
    try:
        foreshadowing = json.loads(book.get("foreshadowing", "[]"))
    except Exception:
        pass
    storylines = []
    try:
        storylines = json.loads(book.get("storylines", "[]"))
    except Exception:
        pass

    target = book.get("target_words", 0) or 600000
    vol_count = max(3, min(12, target // 80000))

    char_desc = "\n".join(f"- {c['name']}：{c['description']}" for c in characters) or "暂无"
    sl_desc = "\n".join(
        f"- {s.get('name', '')}（{s.get('type', '')}）：{s.get('description', '')}"
        for s in storylines
    ) or "暂无"
    fs_desc = "\n".join(f"- {f.get('name', '')}：{f.get('description', '')}" for f in foreshadowing) or "暂无"

    system = (
        "你是一个资深网文架构师，擅长规划长篇小说的分卷结构。\n"
        f"用户要求你规划一部约 {target} 字的小说分卷结构。\n\n"
        "严格输出一个 JSON 对象，包含：\n"
        "- total_volumes：总卷数（整数）\n"
        "- volumes：分卷数组，每项包含：\n"
        "  - number：卷序号（从 1 开始）\n"
        "  - title：卷名（10字以内，要能体现本卷核心内容）\n"
        "  - subtitle：副标题（15字以内，补充卷名）\n"
        "  - estimated_words：本卷预计字数（整数）\n"
        "  - chapter_count：本卷章节数（整数）\n"
        "  - summary_brief：本卷方向概要（50字以内，描述主要情节走向）\n\n"
        f"要求：\n"
        f"- 总卷数约 {vol_count} 卷（每卷约 8-12 万字）\n"
        f"- 各卷字数之和应接近 {target} 字\n"
        f"- 卷名要有吸引力，体现核心冲突或看点\n"
        f"- 各卷之间剧情递进，承上启下\n"
        "不要输出其他内容，只输出 JSON。"
    )
    user = (
        f"书名：{book.get('title', '')}\n"
        f"题材：{book.get('genre', '')}\n"
        f"简介：{book.get('brief', '')}\n"
        f"创作意图：{book.get('author_intent', '')}\n"
        f"爽点方向：{book.get('excitement_direction', '')}\n"
        f"钩子类型：{book.get('hook_type', '')}\n"
        f"世界观设定：{book.get('world_building', '')}\n\n"
        f"角色：\n{char_desc}\n\n"
        f"故事线：\n{sl_desc}\n\n"
        f"伏笔：\n{fs_desc}"
    )

    try:
        wizard._ensure_client()
        raw = wizard._chat(system, user, max_tokens=2048, temperature=0.7)
        data = json.loads(raw)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"规划失败: {str(e)}"}, status_code=500)

    total = data.get("total_volumes", vol_count)
    vols = data.get("volumes", [])
    if not vols:
        return JSONResponse({"error": "AI 未返回有效的分卷规划"}, status_code=500)

    # 清除旧的分卷和大纲
    db_conn = get_db()
    db_conn.execute("DELETE FROM volumes WHERE book_id=?", (book_id,))
    db_conn.execute("DELETE FROM outlines WHERE book_id=?", (book_id,))
    db_conn.commit()
    db_conn.close()

    # 写入 planned_volumes 到 book
    NovelDB.update_book(book_id, planned_volumes=total)

    # 创建所有卷的占位记录
    created = []
    for vp in vols:
        vn = vp.get("number", len(created) + 1)
        v = NovelDB.create_volume(
            book_id=book_id,
            number=vn,
            title=vp.get("title", f"第{vn}卷"),
            subtitle=vp.get("subtitle", ""),
            summary="",
            status="planned",
            estimated_words=vp.get("estimated_words", 0),
            chapter_count=vp.get("chapter_count", 0),
        )
        created.append(v)

    return JSONResponse({"volumes": created, "count": len(created), "total_volumes": total})


@app.post("/api/books/{book_id}/generate-volume")
async def api_generate_volume(book_id: str, volume_number: int = Form(...)):
    """生成阶段：为指定卷生成详细大纲。volume_number 必填。"""
    book = NovelDB.get_book(book_id)
    if not book:
        return JSONResponse({"error": "作品不存在"}, status_code=404)

    characters = NovelDB.list_characters(book_id)
    existing_volumes = NovelDB.list_volumes(book_id)

    foreshadowing = []
    try:
        foreshadowing = json.loads(book.get("foreshadowing", "[]"))
    except Exception:
        pass
    storylines = []
    try:
        storylines = json.loads(book.get("storylines", "[]"))
    except Exception:
        pass

    target = book.get("target_words", 0) or 600000

    # 找到目标卷
    existing_vol = None
    for v in existing_volumes:
        if v["number"] == volume_number:
            existing_vol = v
            break

    char_desc = "\n".join(f"- {c['name']}：{c['description']}" for c in characters) or "暂无"
    sl_desc = "\n".join(
        f"- {s.get('name', '')}（{s.get('type', '')}）：{s.get('description', '')}"
        for s in storylines
    ) or "暂无"
    fs_desc = "\n".join(f"- {f.get('name', '')}：{f.get('description', '')}" for f in foreshadowing) or "暂无"

    # 已有卷的概要（用于上下文）
    vol_context = ""
    if existing_volumes:
        vol_lines = []
        for v in sorted(existing_volumes, key=lambda x: x["number"]):
            s = v.get("summary", "")
            if s:
                vol_lines.append(f"第{v['number']}卷「{v.get('title', '')}」：{s}")
        if vol_lines:
            vol_context = "\n已有分卷概要：\n" + "\n".join(vol_lines)

    # 前面已生成卷的上下文
    prev_vols = [v for v in existing_volumes if v["number"] < volume_number and v.get("summary")]
    prev_context = ""
    if prev_vols:
        prev_lines = []
        for v in sorted(prev_vols, key=lambda x: x["number"]):
            hook = v.get("end_hook", "")
            prev_lines.append(
                f"第{v['number']}卷「{v.get('title', '')}」：{v.get('summary', '')}"
                + (f"\n  卷尾钩子：{hook}" if hook else "")
            )
        prev_context = "\n前面的卷：\n" + "\n".join(prev_lines)

    # 计算 chapter_start
    ch_start = 1
    for v in existing_volumes:
        if v["number"] < volume_number and v.get("chapter_end", 0) > 0:
            ch_start = max(ch_start, v["chapter_end"] + 1)

    system = (
        "你是一个资深网文架构师，擅长规划长篇小说的分卷结构。\n"
        f"用户要求你规划第{volume_number}卷的详细大纲。\n\n"
        "严格输出一个 JSON 对象，包含以下字段：\n"
        "- number：卷序号\n"
        "- title：卷名（10字以内）\n"
        "- subtitle：副标题（15字以内）\n"
        "- chapter_start：起始章节号\n"
        "- chapter_end：结束章节号\n"
        "- summary：本卷概要（200字以内）\n"
        "- key_nodes：关键节点数组（3-5个字符串，每个具体描述一个关键事件，不要带序号或符号前缀，直接写内容）\n"
        "- emotion_arc：情绪弧线（用→连接）\n"
        "- characters_in_vol：本卷重点角色名数组\n"
        "- end_hook：卷尾钩子（50字以内）\n"
        "- estimated_words：本卷预计字数（整数）\n"
        "- chapter_count：本卷章节数（整数）\n"
        "- theme：本卷核心主题\n"
        "- main_conflict：本卷主要冲突\n"
        "- turning_point：关键转折点\n"
        "- character_arc：角色成长弧线\n"
        "- world_change：世界观/势力变化\n"
        "- foreshadowing_plan：伏笔规划（用换行分隔每条伏笔，每条 50 字以内）\n"
        "- emotional_tone：情感基调\n"
        "- climax：高潮设计\n\n"
        f"要求：\n"
        f"- chapter_start 从 {ch_start} 开始\n"
        f"- 与前面的卷衔接自然，承上启下\n"
        f"- 关键节点要具体\n"
        f"- 情绪弧线要有起伏变化\n"
        f"- 卷尾钩子要留下悬念\n"
        "不要输出其他内容，只输出 JSON。"
        )

    user = (
        f"书名：{book.get('title', '')}\n"
        f"题材：{book.get('genre', '')}\n"
        f"简介：{book.get('brief', '')}\n"
        f"创作意图：{book.get('author_intent', '')}\n"
        f"爽点方向：{book.get('excitement_direction', '')}\n"
        f"钩子类型：{book.get('hook_type', '')}\n"
        f"世界观设定：{book.get('world_building', '')}\n"
        f"目标总字数：{target}\n\n"
        f"角色：\n{char_desc}\n\n"
        f"故事线：\n{sl_desc}\n\n"
        f"伏笔：\n{fs_desc}"
        f"{vol_context}"
    )
    if prev_context:
        user += prev_context

    try:
        wizard._ensure_client()
        raw = wizard._chat(system, user, max_tokens=4096, temperature=0.7)
        data = json.loads(raw)

        if isinstance(data, list):
            data = data[0] if data else {}
        if not isinstance(data, dict):
            return JSONResponse({"error": "LLM 返回格式错误"}, status_code=500)

        # 更新已有占位卷
        if existing_vol:
            NovelDB.update_volume(
                existing_vol["id"],
                title=data.get("title", existing_vol.get("title", "")),
                subtitle=data.get("subtitle", ""),
                summary=data.get("summary", ""),
                chapter_count=data.get("chapter_count", 0),
                chapter_start=data.get("chapter_start", 0),
                chapter_end=data.get("chapter_end", 0),
                theme=data.get("theme", ""),
                main_conflict=data.get("main_conflict", ""),
                turning_point=data.get("turning_point", ""),
                character_arc=data.get("character_arc", ""),
                world_change=data.get("world_change", ""),
                foreshadowing_plan=clean_text_list(data.get("foreshadowing_plan", "")),
                emotional_tone=data.get("emotional_tone", ""),
                climax=data.get("climax", ""),
                emotion_arc=data.get("emotion_arc", ""),
                end_hook=data.get("end_hook", ""),
                estimated_words=data.get("estimated_words", 0),
                key_nodes=json.dumps(clean_key_nodes(data.get("key_nodes", [])), ensure_ascii=False),
                characters_in_vol=json.dumps(data.get("characters_in_vol", []), ensure_ascii=False),
            )
            v = NovelDB.get_volume(existing_vol["id"])
        else:
            v = NovelDB.create_volume(
                book_id=book_id,
                number=data.get("number", volume_number),
                title=data.get("title", ""),
                subtitle=data.get("subtitle", ""),
                summary=data.get("summary", ""),
                chapter_count=data.get("chapter_count", 0),
                chapter_start=data.get("chapter_start", 0),
                chapter_end=data.get("chapter_end", 0),
                theme=data.get("theme", ""),
                main_conflict=data.get("main_conflict", ""),
                turning_point=data.get("turning_point", ""),
                character_arc=data.get("character_arc", ""),
                world_change=data.get("world_change", ""),
                foreshadowing_plan=clean_text_list(data.get("foreshadowing_plan", "")),
                emotional_tone=data.get("emotional_tone", ""),
                climax=data.get("climax", ""),
                emotion_arc=data.get("emotion_arc", ""),
                end_hook=data.get("end_hook", ""),
                estimated_words=data.get("estimated_words", 0),
                key_nodes=json.dumps(clean_key_nodes(data.get("key_nodes", [])), ensure_ascii=False),
                characters_in_vol=json.dumps(data.get("characters_in_vol", []), ensure_ascii=False),
                status="planned",
            )
        return JSONResponse({"volume": v})

    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        return JSONResponse({"error": f"生成失败: {str(e)}"}, status_code=500)


@app.post("/api/books/{book_id}/outlines")
async def api_create_outline(book_id: str, chapter_number: int = Form(...),
                              title: str = Form(""), outline_content: str = Form(""),
                              volume_id: int = Form(None), word_target: int = Form(2000),
                              conflict: str = Form(""), excitement: str = Form(""),
                              hook: str = Form(""), storyline: str = Form(""),
                              foreshadowing: str = Form(""), foreshadowing_payoff: str = Form("")):
    o = NovelDB.create_outline(book_id, chapter_number, title, outline_content,
                                volume_id, word_target,
                                conflict, excitement, hook, storyline, foreshadowing, foreshadowing_payoff)
    return JSONResponse(o)


@app.post("/api/outlines/{outline_id}/update")
async def api_update_outline(outline_id: int, chapter_number: int = Form(None),
                              title: str = Form(None), outline_content: str = Form(None),
                              word_target: int = Form(None), status: str = Form(None),
                              volume_id: int = Form(None),
                              conflict: str = Form(None), excitement: str = Form(None),
                              hook: str = Form(None), storyline: str = Form(None),
                              foreshadowing: str = Form(None), foreshadowing_payoff: str = Form(None)):
    kwargs = {}
    if chapter_number is not None: kwargs["chapter_number"] = chapter_number
    if title is not None: kwargs["title"] = title
    if outline_content is not None: kwargs["outline_content"] = outline_content
    if word_target is not None: kwargs["word_target"] = word_target
    if status is not None: kwargs["status"] = status
    if volume_id is not None: kwargs["volume_id"] = volume_id
    if conflict is not None: kwargs["conflict"] = conflict
    if excitement is not None: kwargs["excitement"] = excitement
    if hook is not None: kwargs["hook"] = hook
    if storyline is not None: kwargs["storyline"] = storyline
    if foreshadowing is not None: kwargs["foreshadowing"] = foreshadowing
    if foreshadowing_payoff is not None: kwargs["foreshadowing_payoff"] = foreshadowing_payoff
    NovelDB.update_outline(outline_id, **kwargs)
    return JSONResponse({"ok": True})



@app.post("/api/outlines/{outline_id}/delete")
async def api_delete_outline(outline_id: int):
    NovelDB.delete_outline(outline_id)
    return JSONResponse({"ok": True})



@app.post("/api/books/{book_id}/injections")
async def api_create_injection(book_id: str, name: str = Form(...),
                                 content: str = Form(...), category: str = Form("style"),
                                 is_active: int = Form(1)):
    inj = NovelDB.create_injection(book_id, name, content, category, is_active)
    return JSONResponse(inj)




@app.post("/api/injections/{inj_id}/update")
async def api_update_injection(inj_id: int, name: str = Form(None),
                                content: str = Form(None), category: str = Form(None),
                                is_active: int = Form(None)):
    kwargs = {}
    if name is not None: kwargs["name"] = name
    if content is not None: kwargs["content"] = content
    if category is not None: kwargs["category"] = category
    if is_active is not None: kwargs["is_active"] = is_active
    NovelDB.update_injection(inj_id, **kwargs)
    return JSONResponse({"ok": True})



@app.post("/api/injections/{inj_id}/delete")
async def api_delete_injection(inj_id: int):
    NovelDB.delete_injection(inj_id)
    return JSONResponse({"ok": True})



# QC质检CRUD API已禁用（写作风格重构后移除，db方法保留）
# @app.post("/api/books/{book_id}/rules")
# async def api_create_rule(book_id: str, name: str = Form(...),
#                                  description: str = Form(""), check_content: str = Form(""),
#                                  severity: str = Form("warning"),
#                                  is_active: int = Form(1)):
#     r = NovelDB.create_qc_rule(book_id, name, description, check_content, severity, is_active)
#     return JSONResponse(r)

# @app.post("/api/rules/{rule_id}/update")
# async def api_update_rule(rule_id: int, name: str = Form(None),
#                            description: str = Form(None), check_content: str = Form(None),
#                            severity: str = Form(None), is_active: int = Form(None)):
#     kwargs = {}
#     if name is not None: kwargs["name"] = name
#     if description is not None: kwargs["description"] = description
#     if check_content is not None: kwargs["check_content"] = check_content
#     if severity is not None: kwargs["severity"] = severity
#     if is_active is not None: kwargs["is_active"] = is_active
#     NovelDB.update_qc_rule(rule_id, **kwargs)
#     return JSONResponse({"ok": True})

# @app.post("/api/rules/{rule_id}/delete")
# async def api_delete_rule(rule_id: int):
#     NovelDB.delete_qc_rule(rule_id)
#     return JSONResponse({"ok": True})



# ── Writing Style API ──

@app.get("/api/writing-style/default")
async def api_get_default_writing_style():
    cfg = NovelDB.get_default_writing_config()
    return JSONResponse(cfg)


@app.post("/api/writing-style/default")
async def api_set_default_writing_style(config: str = Form("{}")):
    try:
        cfg = json.loads(config)
    except (json.JSONDecodeError, TypeError):
        cfg = {}
    NovelDB.set_default_writing_config(cfg)
    return JSONResponse({"ok": True})


@app.get("/api/books/{book_id}/writing-style")
async def api_get_book_writing_style(book_id: str):
    merged, book_cfg, default_cfg, is_custom = NovelDB.get_book_writing_config(book_id)
    return JSONResponse({
        "merged": merged,
        "book_config": book_cfg,
        "default_config": default_cfg,
        "is_custom": is_custom,
    })


@app.post("/api/books/{book_id}/writing-style")
async def api_set_book_writing_style(book_id: str, config: str = Form("{}")):
    try:
        cfg = json.loads(config)
    except (json.JSONDecodeError, TypeError):
        cfg = {}
    NovelDB.update_book(book_id, writing_config=json.dumps(cfg, ensure_ascii=False))
    return JSONResponse({"ok": True})


@app.post("/api/books/{book_id}/writing-style/reset")
async def api_reset_book_writing_style(book_id: str):
    NovelDB.update_book(book_id, writing_config="{}")
    return JSONResponse({"ok": True})


# ── Writers API ──

BUILTIN_WRITER_IDS = {w["id"] for w in WRITERS}


def _get_custom_writers():
    raw = NovelDB.get_config("custom_writers", "[]")
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []


def _save_custom_writers(list_):
    NovelDB.set_config("custom_writers", json.dumps(list_, ensure_ascii=False))


def _get_all_writers():
    return WRITERS + _get_custom_writers()


def _get_all_writers_map():
    m = {w["id"]: w for w in WRITERS}
    m.update({w["id"]: w for w in _get_custom_writers()})
    return m


@app.get("/api/writers")
async def api_list_writers():
    return JSONResponse(_get_all_writers())


@app.post("/api/writers")
async def api_create_writer(request: Request):
    form = await request.form()
    import uuid
    writer_id = "custom-" + uuid.uuid4().hex[:8]
    writer_data = {
        "id": writer_id,
        "name": form.get("name", "未命名写手"),
        "avatar": form.get("avatar", "✏️"),
        "style": form.get("style", ""),
        "description": form.get("description", ""),
        "genres": [g.strip() for g in form.get("genres", "").split(",") if g.strip()],
        "config": {
            "writing_rules": form.get("writing_rules", ""),
            "behavior_locks": form.get("behavior_locks", ""),
            "prohibited_words": form.get("prohibited_words", ""),
            "advanced": {
                "natural_dialogue": form.get("natural_dialogue", "true") == "true",
                "no_useless_details": form.get("no_useless_details", "true") == "true",
                "max_env_sentences": int(form.get("max_env_sentences", 3)),
                "max_inner_sentences": int(form.get("max_inner_sentences", 3)),
            },
        },
    }
    custom = _get_custom_writers()
    custom.append(writer_data)
    _save_custom_writers(custom)
    return JSONResponse(writer_data)


@app.put("/api/writers/{writer_id}")
async def api_update_writer(writer_id: str, request: Request):
    form = await request.form()
    all_map = _get_all_writers_map()
    if writer_id not in all_map:
        return JSONResponse({"error": "写手不存在"}, status_code=404)

    updated = {
        "id": writer_id,
        "name": form.get("name", ""),
        "avatar": form.get("avatar", ""),
        "style": form.get("style", ""),
        "description": form.get("description", ""),
        "genres": [g.strip() for g in form.get("genres", "").split(",") if g.strip()],
        "config": {
            "writing_rules": form.get("writing_rules", ""),
            "behavior_locks": form.get("behavior_locks", ""),
            "prohibited_words": form.get("prohibited_words", ""),
            "advanced": {
                "natural_dialogue": form.get("natural_dialogue", "true") == "true",
                "no_useless_details": form.get("no_useless_details", "true") == "true",
                "max_env_sentences": int(form.get("max_env_sentences", 3)),
                "max_inner_sentences": int(form.get("max_inner_sentences", 3)),
            },
        },
    }

    if writer_id in BUILTIN_WRITER_IDS:
        # Builtin: save overrides to custom_writers
        custom = _get_custom_writers()
        found = False
        for i, w in enumerate(custom):
            if w["id"] == writer_id:
                custom[i] = updated
                found = True
                break
        if not found:
            custom.append(updated)
        _save_custom_writers(custom)
    else:
        # Custom: update in-place
        custom = _get_custom_writers()
        for i, w in enumerate(custom):
            if w["id"] == writer_id:
                custom[i] = updated
                break
        _save_custom_writers(custom)

    return JSONResponse(updated)


@app.delete("/api/writers/{writer_id}")
async def api_delete_writer(writer_id: str):
    if writer_id in BUILTIN_WRITER_IDS:
        return JSONResponse({"error": "内置写手不能删除"}, status_code=400)
    custom = _get_custom_writers()
    before = len(custom)
    custom = [w for w in custom if w["id"] != writer_id]
    if len(custom) == before:
        return JSONResponse({"error": "写手不存在"}, status_code=404)
    _save_custom_writers(custom)
    return JSONResponse({"ok": True})


@app.post("/api/writers/{writer_id}/apply")
async def api_apply_writer(writer_id: str, book_id: str = Form(...)):
    writer_data = _get_all_writers_map().get(writer_id)
    if not writer_data:
        return JSONResponse({"error": "写手不存在"}, status_code=404)
    book = NovelDB.get_book(book_id)
    if not book:
        return JSONResponse({"error": "作品不存在"}, status_code=404)
    config = writer_data["config"]
    NovelDB.update_book(book_id,
                        writer_id=writer_id,
                        writing_config=json.dumps(config, ensure_ascii=False))
    return JSONResponse({"ok": True, "writing_config": config})


def _apply_writer_to_book(book_id, writer_id):
    """Apply a writer's config to a book's writing_config."""
    writer_data = _get_all_writers_map().get(writer_id)
    if not writer_data:
        return
    config = writer_data["config"]
    NovelDB.update_book(book_id,
                        writer_id=writer_id,
                        writing_config=json.dumps(config, ensure_ascii=False))


@app.get("/api/writers/{writer_id}")
async def api_get_writer(writer_id: str):
    writer_data = _get_all_writers_map().get(writer_id)
    if not writer_data:
        return JSONResponse({"error": "写手不存在"}, status_code=404)
    return JSONResponse(writer_data)


@app.get("/api/config/default-writer")
async def api_get_default_writer():
    writer_id = NovelDB.get_config("default_writer_id", "")
    return JSONResponse({"writer_id": writer_id})


@app.post("/api/config/default-writer")
async def api_set_default_writer(writer_id: str = Form("")):
    NovelDB.set_config("default_writer_id", writer_id)
    return JSONResponse({"ok": True, "writer_id": writer_id})


# ── Writing API ──

@app.post("/api/books/{book_id}/write")
async def api_write_chapter(book_id: str, chapter_number: int = Form(...),
                             outline_content: str = Form(None)):
    try:
        result = writer.write_chapter(book_id, chapter_number, outline_content)
        return JSONResponse(result)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"生成失败: {str(e)}"}, status_code=500)


from starlette.responses import StreamingResponse


@app.post("/api/books/{book_id}/batch-write")
async def api_batch_write(book_id: str, start_chapter: int = Form(1), end_chapter: int = Form(0)):
    """SSE 批量生成章节（方案 D：骨架→扩写的多轮对话链式生成）。"""
    book = NovelDB.get_book(book_id)
    if not book:
        return JSONResponse({"error": "未找到该书"}, status_code=404)

    all_outlines = NovelDB.list_outlines(book_id)
    outline_map = {o["chapter_number"]: o for o in all_outlines}

    if end_chapter == 0:
        end_chapter = max(outline_map.keys()) if outline_map else 0
    if end_chapter < start_chapter:
        return JSONResponse({"error": "end_chapter 必须 >= start_chapter"}, status_code=400)

    chapter_numbers = list(range(start_chapter, end_chapter + 1))

    async def generate():
        import asyncio
        import queue
        yield f"data: {json.dumps({'phase': 'generate', 'status': 'start', 'total': len(chapter_numbers)})}\n\n"
        for i, ch_num in enumerate(chapter_numbers):
            yield f"data: {json.dumps({'phase': 'generate', 'status': 'chapter_start', 'chapter_number': ch_num, 'index': i + 1, 'total': len(chapter_numbers)})}\n\n"
            try:
                # 用队列从线程中收集流式 token
                token_queue = queue.Queue()
                def status_callback(msg):
                    if isinstance(msg, dict) and msg.get("type") == "token":
                        token_queue.put(msg)
                    else:
                        token_queue.put({"type": "status", "text": msg})

                def run_write():
                    return writer.write_chapter(book_id, ch_num, status_callback=status_callback)

                task = asyncio.get_event_loop().run_in_executor(None, run_write)
                # 持续从队列中读取 token 并推送
                result = None
                while not task.done():
                    try:
                        msg = token_queue.get(timeout=0.1)
                        if msg.get("type") == "token":
                            yield f"data: {json.dumps({'ok': True, 'phase': 'generate', 'status': 'token', 'chapter_number': ch_num, 'text': msg['text'], 'content': msg['content']})}\n\n"
                    except queue.Empty:
                        await asyncio.sleep(0.05)
                # 获取最终结果
                result = await task
                yield f"data: {json.dumps({'ok': True, 'phase': 'generate', 'status': 'chapter_done', 'chapter_number': ch_num, 'title': result.get('title',''), 'word_count': result.get('word_count',0)})}\n\n"
            except Exception as e2:
                import traceback
                error_detail = traceback.format_exc()
                print(f"[BATCH-WRITE ERROR] chapter {ch_num}: {error_detail}", file=sys.stderr)
                err_msg = str(e2).strip() or repr(e2) or '生成失败，请查看后端日志'
                yield f"data: {json.dumps({'ok': False, 'phase': 'generate', 'status': 'chapter_done', 'chapter_number': ch_num, 'error': err_msg})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Total-Chapters": str(len(chapter_numbers))},
    )


@app.post("/api/books/{book_id}/regenerate")
async def api_regenerate_chapter(book_id: str, chapter_number: int = Form(...)):
    try:
        result = writer.regenerate_chapter(book_id, chapter_number)
        return JSONResponse(result)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"生成失败: {str(e)}"}, status_code=500)


@app.post("/api/chapters/{chapter_id}/approve")
async def api_approve_chapter(chapter_id: int):
    writer.approve_chapter(chapter_id)
    return JSONResponse({"ok": True})


@app.post("/api/chapters/{chapter_id}/update")
async def api_update_chapter(chapter_id: int, title: str = Form(None),
                              content: str = Form(None), word_count: int = Form(None)):
    ch = NovelDB.get_chapter(chapter_id)
    if not ch:
        return JSONResponse({"error": "章节不存在"}, status_code=404)
    kwargs = {}
    if title is not None:
        kwargs["title"] = title
    if content is not None:
        kwargs["content"] = content
        kwargs["summary"] = content[:200].replace("\n", " ").strip()
    if word_count is not None:
        kwargs["word_count"] = word_count
    if kwargs:
        NovelDB.update_chapter(chapter_id, **kwargs)
    return JSONResponse({"ok": True})


@app.post("/api/chapters/{chapter_id}/qc")
async def api_qc_chapter(chapter_id: int):
    results = writer.run_qc(chapter_id)
    return JSONResponse({"results": results})


@app.post("/api/config")
async def api_set_config(api_key: str = Form(""), base_url: str = Form(""),
                          model: str = Form(""), default_writer_id: str = Form(None)):
    if api_key:
        NovelDB.set_config("api_key", api_key)
    if base_url:
        NovelDB.set_config("base_url", base_url)
    if model:
        NovelDB.set_config("model", model)
    if default_writer_id is not None:
        NovelDB.set_config("default_writer_id", default_writer_id)
    return JSONResponse({"ok": True})


@app.get("/api/config/default-writer")
async def api_get_default_writer():
    writer_id = NovelDB.get_config("default_writer_id", "")
    return JSONResponse({"writer_id": writer_id})


@app.post("/api/config/default-writer")
async def api_set_default_writer(writer_id: str = Form("")):
    NovelDB.set_config("default_writer_id", writer_id)
    return JSONResponse({"ok": True})


# ── Wizard API ──

@app.post("/api/wizard/suggest-ideas")
async def api_wizard_suggest_ideas():
    try:
        candidates = wizard.suggest_ideas()
        return JSONResponse({"candidates": candidates})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"创意推荐失败: {str(e)}"}, status_code=500)


@app.post("/api/wizard/genres")
async def api_wizard_genres(idea: str = Form(...)):
    try:
        candidates = wizard.suggest_genres(idea)
        return JSONResponse({"candidates": candidates})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"生成失败: {str(e)}"}, status_code=500)


@app.post("/api/wizard/names")
async def api_wizard_names(idea: str = Form(...), genre: str = Form(...)):
    try:
        candidates = wizard.suggest_names(idea, genre)
        return JSONResponse({"candidates": candidates})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": f"生成失败: {str(e)}"}, status_code=500)


@app.post("/api/wizard/generate")
async def api_wizard_generate(
    idea: str = Form(...),
    genre: str = Form(...),
    title: str = Form(...),
    brief: str = Form(""),
    target_words: int = Form(600000),
    writer_id: str = Form(""),
):
    try:
        writer_style = ""
        writers_map = _get_all_writers_map()
        if writer_id and writer_id in writers_map:
            writer_style = writers_map[writer_id]["description"]

        settings = wizard.generate_settings(idea, genre, title, brief, target_words, writer_style)

        # 创建 book
        book = NovelDB.create_book(
            title=title or settings.get("title", ""),
            genre=genre or settings.get("genre", ""),
            brief=brief or settings.get("brief", ""),
            author_intent=settings.get("author_intent", ""),
            writer_id=writer_id,
            target_words=target_words,
        )
        book_id = book["id"]

        # 写入爽点方向、钩子类型、故事线
        NovelDB.update_book(
            book_id,
            excitement_direction=settings.get("excitement_direction", ""),
            hook_type=settings.get("hook_type", ""),
            storylines=json.dumps(settings.get("storylines", []), ensure_ascii=False),
            world_building=settings.get("world_setting", ""),
        )

        # 写入写作风格到 writing_config（写手专属配置 + LLM 生成的规则追加）
        if writer_id and writer_id in writers_map:
            writer_config = writers_map[writer_id]["config"].copy()
            style = settings.get("writing_style", "")
            if style:
                existing_rules = writer_config.get("writing_rules", "")
                writer_config["writing_rules"] = (existing_rules + "\n" + style).strip() if existing_rules else style
            NovelDB.update_book(book_id, writing_config=json.dumps(writer_config, ensure_ascii=False))
        else:
            style = settings.get("writing_style", "")
            if style:
                NovelDB.update_book(book_id, writing_config=json.dumps(
                    {"writing_rules": style}, ensure_ascii=False
                ))

        # 写入爽点/钩子（保留 injections 作为辅助参考）
        for i, hook in enumerate(settings.get("hooks", []), 1):
            NovelDB.create_injection(book_id, f"爽点{i}", hook, "hook", 1)

        # 写入角色
        for ch in settings.get("characters", []):
            NovelDB.create_character(
                book_id,
                name=ch.get("name", ""),
                description=ch.get("description", ""),
                background=ch.get("background", ""),
                traits=ch.get("traits", []),
                appearance=ch.get("appearance", ""),
                relationships=ch.get("relationships", []),
            )

        # 写入分卷（暂时禁用，后续单独优化分卷大纲生成）
        # for vol in settings.get("volumes", []):
        #     NovelDB.create_volume(
        #         book_id,
        #         number=vol.get("number", 1),
        #         title=vol.get("title", ""),
        #         summary=vol.get("summary", ""),
        #         chapter_count=vol.get("chapter_count", 0),
        #     )

        return JSONResponse({"book_id": book_id, "settings": settings})
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        tb = traceback.format_exc()
        print(tb, file=sys.stderr)
        return JSONResponse({"error": f"生成失败: {str(e)}", "traceback": tb}, status_code=500)


# ═══════════════════════════════════════════════════════════════════
# Vue3 SPA 静态文件服务（桌面版 / 生产模式）
# ═══════════════════════════════════════════════════════════════════

_VUE_DIST = BASE / "frontend" / "dist"  # 打包后：_internal/frontend/dist
if not _VUE_DIST.exists():
    _VUE_DIST = PROJECT_ROOT / "frontend" / "dist"  # 开发模式：项目根目录/frontend/dist
if _VUE_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_VUE_DIST / "assets")), name="vue-assets")

    @app.get("/{full_path:path}")
    async def serve_vue_spa(full_path: str):
        """Catch-all: Vue3 SPA 路由"""
        file_path = _VUE_DIST / full_path
        if file_path.is_file():
            return HTMLResponse(file_path.read_text(encoding="utf-8"))
        return HTMLResponse((_VUE_DIST / "index.html").read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════════
# 启动
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json as _json
    _config_file = Path(__file__).parent / "config.json"
    if _config_file.exists():
        try: _cfg = _json.loads(_config_file.read_text(encoding='utf-8'))
        except: _cfg = {}
    else:
        _cfg = {}
    _port = _cfg.get("port", 8000)
    uvicorn.run("main:app", host="127.0.0.1", port=_port, reload=False, log_level="info")












