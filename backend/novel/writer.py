"""LLM 写章节逻辑 — 调用 OpenAI 兼容 API"""

import json
import re
from openai import OpenAI
from .models import get_db
from .db import NovelDB
from .prompts import build_chapter_prompt


class NovelWriter:
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

    def write_chapter(self, book_id, chapter_number, outline_content=None, status_callback=None):
        """生成一章正文，返回生成的文本。status_callback: 可选的回调函数，用于推送中间状态。"""
        def notify(msg):
            if status_callback:
                status_callback(msg)

        self._ensure_client()
        notify("正在准备上下文...")

        book = NovelDB.get_book(book_id)
        characters = NovelDB.list_characters(book_id)
        memories = NovelDB.get_active_memories(book_id)
        recent_chapters = NovelDB.get_chapter_summaries(book_id, limit=5)

        # 获取上一章结尾文本（确保连贯衔接）
        prev_ending = ""
        prev_ch = NovelDB.get_chapter_by_number(book_id, chapter_number - 1)
        if prev_ch and prev_ch.get("content"):
            prev_ending = prev_ch["content"][-800:]

        # 使用三级合并的写作风格配置（全局默认 + 写手专属 + 单本覆盖）
        merged_cfg, _, _, _ = NovelDB.get_book_writing_config(book_id)
        book["writing_config"] = merged_cfg

        # 检查是否已有 outline
        outlines = NovelDB.list_outlines(book_id)
        outline = None
        for o in outlines:
            if o["chapter_number"] == chapter_number:
                outline = o
                break

        # 如果明确传了 outline 内容，覆盖
        if outline_content and outline:
            outline["outline_content"] = outline_content

        # 按需过滤角色：只传本章相关的角色
        relevant_chars = self._filter_relevant_characters(characters, outline)
        if not relevant_chars:
            relevant_chars = characters  # 如果过滤后为空， fallback 到全部角色

        # 按相关性过滤记忆：最近 N 章 + 和当前章节相关的
        relevant_memories = self._filter_relevant_memories(memories, outline, recent_chapters)
        notify("正在构建 prompt...")

        system_prompt, user_prompt = build_chapter_prompt(
            book, relevant_chars, outline, relevant_memories, recent_chapters, prev_ending
        )

        # 动态计算 max_tokens：中文约 1 字 = 1.5-2 tokens，留 1.8 倍余量
        max_words = merged_cfg.get("max_words", 4000)
        dynamic_max_tokens = int(max_words * 1.8)
        # 确保在合理范围内
        dynamic_max_tokens = max(2048, min(dynamic_max_tokens, 12288))

        notify("正在调用 AI 模型生成正文...")
        # 流式输出
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=dynamic_max_tokens,
            stream=True,
        )

        content = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                content += token
                if status_callback:
                    status_callback({"type": "token", "text": token, "content": content})

        word_count = len(content.replace(" ", "").replace("\n", ""))

        # 提取标题
        title = outline["title"] if outline and outline.get("title") else f"第{chapter_number}章"
        # 尝试从正文首行提取标题
        first_line = content.split("\n")[0].strip()
        for p in ["## ", "# ", "第"]:
            if first_line.startswith(p):
                title = first_line.lstrip("#").strip()
                content = "\n".join(content.split("\n")[1:]).strip()
                break

        # 提取章节摘要（取前 200 字作为摘要）
        summary = content[:200].replace("\n", " ").strip()

        # 写入数据库
        existing = NovelDB.get_chapter_by_number(book_id, chapter_number)
        if existing:
            NovelDB.update_chapter(
                existing["id"],
                title=title,
                content=content,
                summary=summary,
                word_count=word_count,
                status="draft",
            )
            chapter_id = existing["id"]
        else:
            ch = NovelDB.create_chapter(
                book_id=book_id,
                chapter_number=chapter_number,
                title=title,
                outline_id=outline["id"] if outline else None,
                content=content,
                summary=summary,
                word_count=word_count,
                status="draft",
            )
            chapter_id = ch["id"]

        # 自动提取记忆 — 后台异步执行，不阻塞返回
        import threading
        threading.Thread(target=self._extract_memory, args=(book_id, chapter_number, content), daemon=True).start()

        return {"chapter_id": chapter_id, "chapter_number": chapter_number, "title": title,
                "word_count": word_count, "content": content, "summary": summary}

    def _filter_relevant_characters(self, characters, outline):
        """根据细纲内容过滤出本章相关的角色。"""
        if not outline:
            return characters

        # 从细纲的 characters_in_vol 字段提取角色名
        relevant_names = set()
        chars_in_vol = outline.get("characters_in_vol", "")
        if chars_in_vol:
            if isinstance(chars_in_vol, str):
                try:
                    parsed = json.loads(chars_in_vol)
                    if isinstance(parsed, list):
                        relevant_names.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    # 逗号/顿号分隔的字符串
                    for name in chars_in_vol.replace("、", ",").replace("，", ",").split(","):
                        name = name.strip()
                        if name:
                            relevant_names.add(name)
            elif isinstance(chars_in_vol, list):
                relevant_names.update(chars_in_vol)

        # 从细纲的 storyline、conflict、outline_content 中提取角色名
        text_fields = [
            outline.get("storyline", ""),
            outline.get("conflict", ""),
            outline.get("outline_content", ""),
        ]
        all_text = " ".join(text_fields)

        for char in characters:
            if char["name"] in all_text:
                relevant_names.add(char["name"])

        # 过滤
        if relevant_names:
            filtered = [c for c in characters if c["name"] in relevant_names]
            return filtered if filtered else characters[:3]  # 至少保留 3 个

        return characters

    def _filter_relevant_memories(self, memories, outline, recent_chapters):
        """按相关性过滤记忆：最近章节的记忆 + 和当前章节相关的记忆。"""
        if not memories:
            return []

        # 最近 3 章的记忆一定保留
        recent_ch_nums = set()
        if recent_chapters:
            for ch in recent_chapters[-3:]:
                recent_ch_nums.add(ch["chapter_number"])

        # 从细纲中提取关键词
        keywords = set()
        if outline:
            for field in ["outline_content", "conflict", "excitement", "hook", "storyline", "foreshadowing", "foreshadowing_payoff"]:
                val = outline.get(field, "")
                if val:
                    # 提取 2-4 字的中文词
                    for word in re.findall(r'[\u4e00-\u9fa5]{2,4}', val):
                        keywords.add(word)

        relevant = []
        seen_facts = set()
        for m in memories:
            # 最近章节的记忆直接保留
            if m["chapter_number"] in recent_ch_nums:
                if m["fact"] not in seen_facts:
                    relevant.append(m)
                    seen_facts.add(m["fact"])
                continue

            # 和当前章节相关的记忆（包含关键词）
            if keywords:
                for kw in keywords:
                    if kw in m["fact"]:
                        if m["fact"] not in seen_facts:
                            relevant.append(m)
                            seen_facts.add(m["fact"])
                        break

        # 限制最多 20 条
        return relevant[:20]

    def _extract_memory(self, book_id, chapter_number, content):
        """从章节内容中提取关键事实存入记忆表。使用全文提取。"""
        try:
            self._ensure_client()

            # 如果内容太长，分段提取
            max_chunk = 6000
            chunks = []
            if len(content) <= max_chunk:
                chunks = [content]
            else:
                # 按段落分割，每段不超过 max_chunk
                paragraphs = content.split("\n")
                current = ""
                for p in paragraphs:
                    if len(current) + len(p) > max_chunk:
                        if current:
                            chunks.append(current)
                        current = p
                    else:
                        current = current + "\n" + p if current else p
                if current:
                    chunks.append(current)

            all_facts = []
            for chunk in chunks:
                extract_prompt = f"""从以下小说章节中，提取所有重要的事实性信息（角色关系变化、关键事件、地点、时间信息等）。
以 JSON 数组格式输出，每个元素包含 "type"（取值：plot/character/relationship/world）和 "fact"（事实描述字符串）。

示例格式：
[{{"type": "plot", "fact": "主角张三在悬崖下发现了神秘洞穴"}}]

小说章节内容：
{chunk}
"""
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": extract_prompt}],
                    temperature=0.1,
                    max_tokens=1024,
                )
                raw = resp.choices[0].message.content.strip()
                if raw.startswith("```"):
                    raw = raw.strip("`").strip()
                    if raw.startswith("json"):
                        raw = raw[4:].strip()
                facts = json.loads(raw)
                if isinstance(facts, list):
                    all_facts.extend(f for f in facts if "type" in f and "fact" in f)

            if all_facts:
                memories = [(f["type"], f["fact"], "auto") for f in all_facts]
                NovelDB.add_memories(book_id, chapter_number, memories)
        except Exception:
            # 提取失败也不影响主流程
            pass

    def approve_chapter(self, chapter_id):
        """标记章节为已批准"""
        NovelDB.update_chapter(chapter_id, status="approved")

    def regenerate_chapter(self, book_id, chapter_number):
        """重新生成章节（先删旧版再生成）"""
        existing = NovelDB.get_chapter_by_number(book_id, chapter_number)
        if existing:
            NovelDB.delete_chapter(existing["id"])
        return self.write_chapter(book_id, chapter_number)

    def run_qc(self, chapter_id):
        """对章节执行简单质检，返回检查报告"""
        ch = NovelDB.get_chapter(chapter_id)
        if not ch:
            return []
        content = ch.get("content", "")
        book_id = ch.get("book_id")
        rules = NovelDB.list_qc_rules(book_id)
        results = []
        for rule in rules:
            if not rule.get("is_active", 1):
                continue
            check = rule.get("check_content", "")
            if check and check in content:
                results.append({
                    "rule": rule["name"],
                    "severity": rule.get("severity", "warning"),
                    "message": f"检测到：{check}",
                    "passed": False,
                })
            else:
                results.append({
                    "rule": rule["name"],
                    "severity": rule.get("severity", "warning"),
                    "message": "未发现问题",
                    "passed": True,
                })
        return results

    # ── 方案 D：骨架→扩写的多轮对话链式生成 ──

    def generate_skeleton(self, book_id, chapter_numbers):
        """阶段一：一次性生成多章骨架（每章 200 字梗概）。"""
        self._ensure_client()

        book = NovelDB.get_book(book_id)
        characters = NovelDB.list_characters(book_id)
        merged_cfg, _, _, _ = NovelDB.get_book_writing_config(book_id)
        outlines = NovelDB.list_outlines(book_id)
        outline_map = {o["chapter_number"]: o for o in outlines}

        # 收集目标章节的细纲
        target_outlines = []
        for num in chapter_numbers:
            ol = outline_map.get(num)
            if ol:
                target_outlines.append(ol)

        char_desc = "\n".join(f"- {c['name']}：{c['description']}" for c in characters) or "暂无"

        # 细纲详情
        outline_desc = ""
        for ol in target_outlines:
            outline_desc += f"\n第{ol['chapter_number']}章「{ol.get('title', '')}」\n"
            if ol.get("outline_content"):
                outline_desc += f"  大纲：{ol['outline_content']}\n"
            for label, key in [("冲突", "conflict"), ("爽点", "excitement"), ("钩子", "hook"),
                               ("故事线", "storyline"), ("伏笔", "foreshadowing"), ("伏笔回收", "foreshadowing_payoff")]:
                if ol.get(key):
                    outline_desc += f"  {label}：{ol[key]}\n"

        # 最近章节摘要
        recent = NovelDB.get_chapter_summaries(book_id, limit=3)
        recent_desc = ""
        if recent:
            recent_desc = "\n最近章节：\n" + "\n".join(
                f"- 第{ch['chapter_number']}章《{ch['title']}》：{ch['summary'][:100]}"
                for ch in recent
            )

        system = (
            "你是一个资深网文大纲策划师。\n"
            "你需要为一组章节生成精炼的骨架梗概，每章约 200 字。\n"
            "骨架要体现：核心场景、关键冲突、人物行动、情绪走向、章末钩子。\n"
            "骨架之间要有明确的递进关系，体现整体弧线。\n\n"
            "严格输出一个 JSON 数组，每个元素包含：\n"
            "- chapter_number：章节序号（整数）\n"
            "- skeleton：骨架梗概（200字以内，描述核心场景、冲突、行动、情绪走向）\n"
            "不要输出其他内容，只输出 JSON。"
        )
        user = (
            f"书名：{book.get('title', '')}\n"
            f"题材：{book.get('genre', '')}\n"
            f"简介：{book.get('brief', '')}\n"
            f"世界观：{book.get('world_building', '')}\n\n"
            f"角色：\n{char_desc}\n"
            f"{recent_desc}\n\n"
            f"本次需要生成以下章节的骨架：\n{outline_desc}\n\n"
            f"请为以上 {len(target_outlines)} 章生成骨架梗概。"
        )

        raw = self._chat(system, user, max_tokens=2048, temperature=0.7)
        skeletons = json.loads(raw)
        if not isinstance(skeletons, list):
            raise ValueError("骨架生成返回格式错误")
        return {s["chapter_number"]: s["skeleton"] for s in skeletons}

    def _chat(self, system, user, max_tokens=4096, temperature=0.7):
        """单次 LLM 调用。"""
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return resp.choices[0].message.content.strip()

    def expand_chapter_batch(self, book_id, chapter_numbers, skeletons):
        """阶段二：多轮对话链式扩写，逐章生成完整正文。"""
        self._ensure_client()

        book = NovelDB.get_book(book_id)
        characters = NovelDB.list_characters(book_id)
        memories = NovelDB.get_active_memories(book_id)
        merged_cfg, _, _, _ = NovelDB.get_book_writing_config(book_id)
        book["writing_config"] = merged_cfg
        outlines = NovelDB.list_outlines(book_id)
        outline_map = {o["chapter_number"]: o for o in outlines}

        # 构建 system prompt（复用 build_chapter_prompt 的逻辑）
        from .prompts import build_chapter_prompt
        # 用第一章的 outline 构建基础 system prompt
        first_outline = outline_map.get(chapter_numbers[0])
        recent_chapters = NovelDB.get_chapter_summaries(book_id, limit=5)
        base_system, _ = build_chapter_prompt(
            book, characters, first_outline, memories, recent_chapters, ""
        )

        # 补充骨架全局视角到 system prompt
        skeleton_overview = "\n\n## 本次批量生成的骨架规划\n"
        for num in chapter_numbers:
            sk = skeletons.get(num, "")
            ol = outline_map.get(num, {})
            skeleton_overview += f"第{num}章「{ol.get('title', '')}」：{sk}\n"
        base_system += skeleton_overview
        base_system += (
            "\n\n## 连贯性要求\n"
            "- 你将连续生成多章正文，每章必须自然衔接上一章的结尾\n"
            "- 保持文风、用词习惯、叙事节奏的一致性\n"
            "- 角色的性格和说话方式必须前后一致\n"
            "- 不要重复上一章已经发生的情节\n"
        )

        # 多轮对话：逐章扩写
        messages = [{"role": "system", "content": base_system}]
        results = []

        for i, ch_num in enumerate(chapter_numbers):
            ol = outline_map.get(ch_num, {})
            skeleton = skeletons.get(ch_num, "")

            # 构建本章的 user message
            user_parts = [f"## 请扩写第{ch_num}章"]
            if ol.get("title"):
                user_parts.append(f"标题：{ol['title']}")
            user_parts.append(f"骨架梗概：{skeleton}")
            if ol.get("outline_content"):
                user_parts.append(f"详细大纲：{ol['outline_content']}")
            if ol.get("word_target"):
                user_parts.append(f"目标字数：{ol['word_target']}字")
            for label, key in [("冲突", "conflict"), ("爽点", "excitement"), ("钩子", "hook"),
                               ("故事线", "storyline"), ("伏笔", "foreshadowing"), ("伏笔回收", "foreshadowing_payoff")]:
                if ol.get(key):
                    user_parts.append(f"{label}：{ol[key]}")
            user_parts.append("\n现在请直接写出本章完整正文。")

            messages.append({"role": "user", "content": "\n".join(user_parts)})

            # 动态计算 max_tokens
            max_words = merged_cfg.get("max_words", 4000)
            dynamic_max_tokens = int(max_words * 1.8)
            dynamic_max_tokens = max(2048, min(dynamic_max_tokens, 12288))

            # 调用 LLM
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.8,
                max_tokens=dynamic_max_tokens,
                stream=False,
            )
            content = resp.choices[0].message.content.strip()
            word_count = len(content.replace(" ", "").replace("\n", ""))

            # 字数检测：超 10% 自动重写，最多重试 2 次
            max_words_limit = merged_cfg.get("max_words", 4000)
            word_count_exceeded = False
            retry_count = 0
            while word_count > max_words_limit * 1.1 and retry_count < 2:
                retry_count += 1
                stricter_user = user_parts[-1] + f"\n\n【重要】上次写了 {word_count} 字，超出了 {max_words_limit} 字上限。这次必须严格控制在 {max_words_limit} 字以内！"
                messages_for_retry = messages[:-1] + [{"role": "user", "content": stricter_user}]
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages_for_retry,
                    temperature=0.7,
                    max_tokens=dynamic_max_tokens,
                    stream=False,
                )
                content = resp.choices[0].message.content.strip()
                word_count = len(content.replace(" ", "").replace("\n", ""))

            if word_count > max_words_limit * 1.1:
                word_count_exceeded = True

            # 提取标题
            title = ol.get("title", "") or f"第{ch_num}章"
            first_line = content.split("\n")[0].strip()
            for p in ["## ", "# ", "第"]:
                if first_line.startswith(p):
                    title = first_line.lstrip("#").strip()
                    content = "\n".join(content.split("\n")[1:]).strip()
                    break

            summary = content[:200].replace("\n", " ").strip()

            # 把 assistant 的回复加入对话历史（多轮连贯）
            messages.append({"role": "assistant", "content": resp.choices[0].message.content})

            # 写入数据库
            existing = NovelDB.get_chapter_by_number(book_id, ch_num)
            if existing:
                NovelDB.update_chapter(
                    existing["id"], title=title, content=content,
                    summary=summary, word_count=word_count, status="draft",
                )
                chapter_id = existing["id"]
            else:
                ch = NovelDB.create_chapter(
                    book_id=book_id, chapter_number=ch_num, title=title,
                    outline_id=ol.get("id") if ol else None,
                    content=content, summary=summary,
                    word_count=word_count, status="draft",
                )
                chapter_id = ch["id"]

            # 提取记忆
            self._extract_memory(book_id, ch_num, content)

            results.append({
                "chapter_id": chapter_id, "chapter_number": ch_num,
                "title": title, "word_count": word_count, "summary": summary,
                "word_count_exceeded": word_count_exceeded, "retry_count": retry_count,
            })

        return results
