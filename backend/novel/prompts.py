"""博学式 Prompt 模板 — 一次生成，上下文丰富，去AI味"""

import json


def build_chapter_prompt(book, characters, outline, memories, recent_chapters, prev_ending="", style_example="", template_author="", volume_info="", characters_upcoming=None, generation_mode=None, first_half_content="", character_states=None):
    """构建写章节的 system + user message。自然叙述风格，去AI味。
    generation_mode: None=单次生成, "first_half"=只写前半段, "second_half"=续写后半段
    first_half_content: 当 generation_mode="second_half" 时，传入前半段已生成的内容
    """

    writing_config = book.get("writing_config", {})
    if isinstance(writing_config, str):
        try:
            writing_config = json.loads(writing_config)
        except (json.JSONDecodeError, TypeError):
            writing_config = {}

    min_words = writing_config.get("min_words", 2000)
    max_words = writing_config.get("max_words", 4000)

    # ═══ 开篇：根据生成模式调整指令 ═══
    if generation_mode == "first_half":
        half_min = min_words // 2
        half_max = max_words // 2
        parts = [f"你现在要写一章网文正文的前半部分，字数大概 {half_min} 到 {half_max}。写到情节推进到一半、一个自然的断点就停。不用写结局，不用收束，写到中间断开就行。直接开始写，不用任何前言后语。"]
    elif generation_mode == "second_half":
        half_min = min_words // 2
        half_max = max_words // 2
        parts = [f"你正在写一章网文正文的后半部分，字数大概 {half_min} 到 {half_max}。前面已经写了一段，你从断的地方接着往下写，一直写到本章结束。直接开始写，不用重复前面的内容。"]
    else:
        parts = [f"你现在要写一章网文正文，字数大概 {min_words} 到 {max_words}。直接开始写，不用任何前言后语。"]

    # ═══ 风格锚点：放在最前面，让 LLM 的语感第一时间被拉过去 ═══
    if style_example:
        parts.append("")
        parts.append("先感受一下这个文风，你写出来的东西应该跟这个是同一个味道：")
        parts.append(style_example)
    if template_author:
        parts.append("")
        parts.append(f"整体感觉往{template_author}那个方向靠。")

    # ═══ 卷内位置 ═══
    if volume_info:
        parts.append("")
        parts.append(volume_info)

    # ═══ 角色情绪差异化 ═══
    parts.append("")
    parts.append("注意：不同角色对同一事件的反应要不一样。结合角色各自的性格、处境和立场来写他们的情绪和反应差异，不要所有角色一个反应。")


    # ═══ 故事背景：自然叙述，不用"简介：xxx"这种标签 ═══
    if book.get("brief"):
        parts.append("")
        parts.append(f"这本书讲的是：{book['brief']}")

    if book.get("author_intent"):
        parts.append("")
        parts.append(f"作者想表达的东西是：{book['author_intent']}")

    if book.get("world_building"):
        parts.append("")
        parts.append(f"故事发生的世界是这样的——{book['world_building']}")

    # ═══ 角色：从"档案卡片"改成"跟人聊角色"的口吻 ═══
    if characters:
        parts.append("")
        parts.append("主要角色的情况：")
        for ch in characters:
            name = ch.get("name", "")
            desc = ch.get("description", "")
            bg = ch.get("background", "")
            traits = ch.get("traits", [])
            appearance = ch.get("appearance", "")
            rels = ch.get("relationships", [])
            speech_style = ch.get("speech_style", "")
            dialogue_sample = ch.get("dialogue_sample", "")

            # 用自然语言拼接，不用顿号分隔的标签
            text = name
            if desc:
                text += f"，{desc}"
            if bg:
                text += f"。{bg}"
            if traits:
                trait_text = "\u3001".join(traits[:3])
                text += f"\u3002\u8fd9\u4eba{trait_text}"
            if appearance:
                text += f"\u3002\u957f\u76f8\u4e0a\uff0c{appearance}"
            if speech_style:
                text += f"\u3002\u8bf4\u8bdd\u98ce\u683c\uff1a{speech_style}"
            if dialogue_sample:
                text += f"\u3002\u4ed6\u8bf4\u8bdd\u5927\u6982\u662f\u8fd9\u79cd\u611f\u89c9\uff1a{dialogue_sample}"
            if ch.get("emotion_profile"):
                text += f"\u3002\u60c5\u7eea\u53cd\u5e94\u4e0a\uff0c{ch['emotion_profile']}"
            if rels:
                rel_texts = []
                for r in rels:
                    if isinstance(r, dict):
                        rel_texts.append(f"{r.get('target','')}是他{r.get('relation','')}")
                if rel_texts:
                    text += f"。关系上，{'，'.join(rel_texts)}"
            text += "。"
            parts.append(text)

    # ═══ 即将登场的角色（伏笔铺垫）═══
    if characters_upcoming:
        upcoming_texts = []
        for ch in characters_upcoming:
            name = ch.get("name", "")
            fav = ch.get("first_appearance_volume") or 1
            desc = ch.get("first_appearance_desc", "")
            brief = ch.get("description", "")[:60]
            text = f"{name}（第{fav}卷才会正式出场"
            if desc:
                text += f"，{desc}"
            elif brief:
                text += f"，{brief}"
            text += "）"
            upcoming_texts.append(text)
        parts.append("")
        parts.append("后面还有这些人要出场，现在可以埋点线索、提一嘴相关的东西，但别让他们直接露面：")
        for t in upcoming_texts:
            parts.append(t)

    # ═══ 写作规则：从列表改成自然段落 ═══
    writing_rules = writing_config.get("writing_rules", "")
    if writing_rules:
        rules_lines = [line.strip() for line in writing_rules.strip().split("\n") if line.strip()]
        if rules_lines:
            parts.append("")
            parts.append("写法上注意这几点——" + "；".join(rules_lines) + "。")

    # ═══ 禁用词 ═══
    prohibited = writing_config.get("prohibited_words", "")
    if prohibited:
        parts.append("")
        parts.append(f"这些词别用：{prohibited}。")

    # ═══ 行为锁：自然化 ═══
    behavior_locks = writing_config.get("behavior_locks", "")
    if behavior_locks:
        lock_lines = [line.strip() for line in behavior_locks.strip().split("\n") if line.strip()]
        if lock_lines:
            parts.append("")
            parts.append("角色行为的红线：" + "；".join(lock_lines) + "。")

    # ═══ 高级设置：融入自然语言 ═══
    advanced = writing_config.get("advanced", {})
    if advanced:
        advs = []
        if advanced.get("natural_dialogue"):
            advs.append("对话要像真人说话，每个人口气不一样，带点个人习惯")
        if advanced.get("no_useless_details"):
            advs.append("环境描写得有用，别为了描写而描写")
        max_env = advanced.get("max_env_sentences", 0)
        if max_env:
            advs.append(f"连着写环境别超过{max_env}句")
        max_inner = advanced.get("max_inner_sentences", 0)
        if max_inner:
            advs.append(f"内心独白一次别超过{max_inner}句")
        if advs:
            parts.append("")
            parts.append("另外——" + "，".join(advs) + "。")

    # ═══════════════════════════════════════════════════════
    # 核心新增：去AI味 + 允许不完美 + 禁止总结癖
    # ═══════════════════════════════════════════════════════
    parts.append("")
    parts.append(
        "写的时候像一个日更六千字的网文作者，不要像AI在写作文。具体来说：\n"
        "句式要有长有短，别每句都差不多长。紧张的地方用短句砸，舒缓的地方可以拖一拖。\n"
        "对话里要有废话和口语——\"嗯\"、\"行吧\"、\"得了吧\"、\"你爱咋咋\"这种，真人说话不会每句都有信息量。\n"
        "角色可以答非所问，可以说到一半岔开，可以用动作代替回答。\n"
        "不要用\"仿佛\"、\"宛如\"、\"似乎\"、\"不禁\"、\"忍不住\"这些词来凑描写，直接写动作和感觉。\n"
        "别在章末搞总结、升华、感悟。写到该断的地方就断——断在一句对话上、一个动作上、一个画面上，干脆利落。\n"
        "不要每段都工整对称，允许有的段落就一句话，有的段落长一点。\n"
        "多用五感来写场景——角色看到什么、听到什么、闻到什么、皮肤感觉到什么（冷热、粗糙、潮湿），别光写角色想了什么。\n"
        "提到已命名的角色时，一律用角色的名字来称呼（比如角色叫\u201c铁锤\u201d就写\u201c铁锤\u201d），不要用职业、身份、外号来代替名字（别写成\u201c铁匠\u201d\u201c那个工匠\u201d\u201c年轻人\u201d这种）。全书角色名字必须前后统一，不能这章叫一个名、下章换另一个。"
    )

    # ═══ 节奏类型：根据 pace_type 给不同的写法指令 ═══
    pace_type = ""
    if outline:
        pace_type = outline.get("pace_type", "")
    if pace_type:
        parts.append("")
        if pace_type == "爆发":
            parts.append("本章是爆发章——节奏要快，短句为主，动作密集。对话要短促有力，少写心理活动，多写外在冲突和动作场面。每段不超过三四句话。")
        elif pace_type == "蓄势":
            parts.append("本章是蓄势章——节奏可以慢，允许更多的环境描写、心理活动和角色互动。为后面的爆发做铺垫，张力藏在细节里。可以写长段落。")
        elif pace_type == "过渡":
            parts.append("本章是过渡章——节奏适中，主要推进剧情和角色关系。可以多写日常对话和角色互动，让读者喘口气，但要保持有趣。")

    # ═══ 分段生成：second_half 模式时，把前半段内容喂进来 ═══
    if generation_mode == "second_half" and first_half_content:
        parts.append("")
        parts.append("前面已经写了这些，你从这里接着往下写，不要重复前面的内容：")
        parts.append(first_half_content[-800:])

    # ═══ 角色当前状态（动态追踪，防瞬移 + 死人防复活）═══
    if character_states:
        alive = [s for s in character_states if s.get("is_alive", 1)]
        dead = [s for s in character_states if not s.get("is_alive", 1)]

        if alive:
            parts.append("")
            parts.append("角色当前状态（必须遵守空间逻辑）：")
            for s in alive:
                name = s.get("name", "")
                location = s.get("location", "") or "未知地点"
                status = s.get("status", "") or "状态不明"
                last_chapter = s.get("last_chapter", 0)
                time_note = s.get("time_note", "")
                line = f"- {name}：目前在 {location}，{status}（第{last_chapter}章最后出现"
                if time_note:
                    line += f"，时间线：{time_note}"
                line += "）"
                parts.append(line)
            parts.append("")
            parts.append(
                "空间一致性约束：角色不能无理由瞬移。如果本章需要某个角色出现在某地，但该角色当前不在那里，"
                "你必须写出合理的转场过程（赶路、时间跳跃、传送、被召唤等），或者换一个在场角色来推进剧情。"
                "如果本章细纲涉及时间跳跃，请在正文开头明确体现，并相应调整角色位置。"
            )

        if dead:
            parts.append("")
            dead_names = "、".join(s["name"] for s in dead)
            parts.append(f"⚠️ 以下角色已经死亡：{dead_names}。他们不能以真人实体的方式出场（即不能活着出现、不能说话、不能行动）。但可以通过其他角色的回忆、幻觉、梦境、灵魂等非实体形式提及或出现。")

    # ═══ 故事记忆 ═══
    if memories:
        parts.append("")
        mem_texts = [f"第{m['chapter_number']}章的时候，{m['fact']}" for m in memories]
        parts.append("故事到目前为止发生过这些事：")
        for mt in mem_texts:
            parts.append(mt)

    # ═══ 最近章节摘要 ═══
    if recent_chapters:
        parts.append("")
        parts.append("前面几章大概是这样：")
        for ch in recent_chapters:
            parts.append(f"第{ch['chapter_number']}章《{ch['title']}》——{ch['summary']}")

    # ═══ 上一章结尾 ═══
    if prev_ending:
        parts.append("")
        parts.append("上一章结尾是这么结束的：")
        parts.append(prev_ending)
        parts.append("")
        parts.append("这是上一章的结尾。直接从这儿接着写，不要复述上面的原文——你的第一句话就是新情节的起点，不是上一章的回顾。")

    system_prompt = "\n".join(parts)

    # ═══ User message ═══
    user_parts = []
    if outline:
        user_parts.append(f"写第{outline['chapter_number']}章。")
        if outline.get("title"):
            user_parts.append(f"标题叫：{outline['title']}")
        if outline.get("outline_content"):
            user_parts.append(f"这章大概讲这些：{outline['outline_content']}")
        if outline.get("word_target"):
            user_parts.append(f"写 {outline['word_target']} 字左右。")
        # 细纲字段合成一段自然叙述
        field_parts = []
        if outline.get("conflict"):
            field_parts.append(f"冲突在{outline['conflict']}")
        if outline.get("excitement"):
            field_parts.append(f"爽点是{outline['excitement']}")
        if outline.get("hook"):
            field_parts.append(f"章末收在{outline['hook']}")
        if outline.get("storyline"):
            field_parts.append(f"推{outline['storyline']}这条线")
        if outline.get("foreshadowing"):
            field_parts.append(f"埋个伏笔：{outline['foreshadowing']}")
        if outline.get("foreshadowing_payoff"):
            field_parts.append(f"收一个伏笔：{outline['foreshadowing_payoff']}")
        if outline.get("emotion"):
            field_parts.append(f"这章情绪基调是{outline['emotion']}")
        if field_parts:
            user_parts.append("，".join(field_parts) + "。")
    else:
        user_parts.append("接着前面的故事往下写。")

    user_parts.append("")
    if generation_mode == "first_half":
        user_parts.append("先写前半段。")
    elif generation_mode == "second_half":
        user_parts.append("接着写后半段。")
    else:
        user_parts.append("开写。")

    user_prompt = "\n".join(user_parts)

    return system_prompt, user_prompt
