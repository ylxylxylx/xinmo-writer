"""博学式 Prompt 模板 — 一次生成，上下文丰富"""

import json


def build_chapter_prompt(book, characters, outline, memories, recent_chapters, prev_ending=""):
    """构建写章节的 system + user message。去掉结构化标题，改用自然段落。"""

    parts = ["你是一位优秀的长篇网络小说作家。直接写出完整的章节内容。注意直接开始写正文，不要输出任何额外说明。"]

    # 字数约束
    writing_config = book.get("writing_config", {})

    # 风格参考
    parts.append("")
    parts.append("参考这样的写法：")
    parts.append("“操。”赵小田骂了一句。")
    parts.append("面前这地，裂得跟龟壳似的，别说种庄稼，撒把种子都能掉缝里去。")
    parts.append("他蹲下来，抓了一把土，捏了捏，又闻了闻——碱的。")
    parts.append("“殿下，要不……咱们换个地方？”身后的老太监小心翼翼地开口。")
    parts.append("“换？”赵小田站起身，拍了拍手，“能换去哪儿？整个京城外头全是这鬼样子。”")
    parts.append("老太监缩了缩脖子，不敢吭声了。")
    parts.append("赵小田没理他，从怀里掏出一袋化肥。")
    parts.append("“就这儿了。”他说。")
    parts.append("")
    parts.append("雨下了三天。")
    parts.append("刘安坐在屋檐下，看着院子里积的水慢慢往屋里漫。")
    parts.append("他没动。")
    parts.append("准确地说，他已经两天没动过了。")
    parts.append("锅里还有半碗粥，馊了。他知道，但他懒得热。")
    parts.append("媳妇儿回娘家了，走的时候摔了门，门栓到现在还歪着。")
    parts.append("他就这么看着。看着水漫进来，漫过门槛，漫到他脚边。")
    parts.append("")
    parts.append("刀砍过来的时候，陈飞没躲。")
    parts.append("不是不想躲，是来不及。")
    parts.append("他的刀还在鞘里，对方的刀已经到了他脖子三寸外。")
    parts.append("完了——他想。")
    parts.append("“铛——”")
    parts.append("一支箭擦着他的耳朵飞过去，正中对方的刀面。")
    parts.append("火星溅了他一脸。")
    parts.append("“发什么愣！”远处传来喊声，“跑啊！”")
    parts.append("陈飞这才反应过来，转身就跑。")

    if isinstance(writing_config, str):
        try:
            writing_config = json.loads(writing_config)
        except (json.JSONDecodeError, TypeError):
            writing_config = {}
    min_words = writing_config.get("min_words", 2000)
    max_words = writing_config.get("max_words", 4000)
    parts.append(f"单章字数控制在 {min_words}-{max_words} 字之间。")

    # 创作意图
    if book.get("author_intent"):
        parts.append("")
        parts.append(f"这部小说的创作意图是：{book['author_intent']}")

    # 故事简介
    if book.get("brief"):
        parts.append("")
        parts.append(book["brief"])

    # 世界观
    if book.get("world_building"):
        parts.append("")
        parts.append(book["world_building"])

    # 角色
    if characters:
        char_texts = []
        for ch in characters:
            desc_parts = []
            name = ch.get("name", "")
            desc = ch.get("description", "")
            bg = ch.get("background", "")
            traits = ch.get("traits", [])
            appearance = ch.get("appearance", "")
            rels = ch.get("relationships", [])

            desc_parts.append(f"{name}")
            if desc:
                desc_parts.append(f"，{desc}")
            if bg:
                desc_parts.append(f"。{bg}")
            if traits:
                desc_parts.append(f"。性格{'、'.join(traits[:3])}")
            if appearance:
                desc_parts.append(f"。{appearance}")
            if rels:
                rel_texts = []
                for r in rels:
                    if isinstance(r, dict):
                        rel_texts.append(f"{r.get('relation','')}（{r.get('target','')}）")
                if rel_texts:
                    desc_parts.append(f"。和{'、'.join(rel_texts)}")
            char_texts.append("".join(desc_parts))
        parts.append("")
        parts.append("故事中有这些人物：")
        for t in char_texts:
            parts.append(t)

    # 写作规则
    writing_rules = writing_config.get("writing_rules", "")
    if writing_rules:
        parts.append("")
        parts.append("写的时候注意：")
        for line in writing_rules.strip().split("\n"):
            line = line.strip()
            if line:
                parts.append(f"· {line}")

    # 禁用词
    prohibited = writing_config.get("prohibited_words", "")
    if prohibited:
        parts.append("")
        parts.append(f"注意避免这些词汇：{prohibited}")

    # 行为锁
    behavior_locks = writing_config.get("behavior_locks", "")
    if behavior_locks:
        parts.append("")
        parts.append("角色的行为约束：")
        for line in behavior_locks.strip().split("\n"):
            line = line.strip()
            if line:
                parts.append(f"· {line}")

    # 高级设置
    advanced = writing_config.get("advanced", {})
    if advanced:
        advs = []
        if advanced.get("natural_dialogue"):
            advs.append("对话要口语化自然，每人口吻有差异，带个人毛边")
        if advanced.get("no_useless_details"):
            advs.append("所有环境描写必须服务情节，不要无用的装饰性细节")
        max_env = advanced.get("max_env_sentences", 0)
        if max_env:
            advs.append(f"连续环境描写不超过{max_env}句")
        max_inner = advanced.get("max_inner_sentences", 0)
        if max_inner:
            advs.append(f"每页内心戏不超过{max_inner}句")
        if advs:
            parts.append("")
            parts.append("写作控制：")
            for p in advs:
                parts.append(f"· {p}")

    # 故事记忆（自然叙述）
    if memories:
        mem_texts = [f"第{m['chapter_number']}章的时候，{m['fact']}" for m in memories]
        parts.append("")
        parts.append("到目前为止，故事已经发展到了这些情节：")
        for mt in mem_texts:
            parts.append(mt)

    # 最近章节摘要
    if recent_chapters:
        parts.append("")
        parts.append("之前几章的故事回顾：")
        for ch in recent_chapters:
            parts.append(f"· 第{ch['chapter_number']}章《{ch['title']}》：{ch['summary']}")

    # 上一章结尾
    if prev_ending:
        parts.append("")
        parts.append("上一章最后写到的地方是：")
        parts.append(prev_ending)

    system_prompt = "\n".join(parts)

    # User message
    user_parts = []
    if outline:
        user_parts.append(f"下面要写的是第{outline['chapter_number']}章。")
        if outline.get("title"):
            user_parts.append(f"章节标题：{outline['title']}")
        if outline.get("outline_content"):
            user_parts.append(f"这章的大致情节是：{outline['outline_content']}")
        if outline.get("word_target"):
            user_parts.append(f"目标写{outline['word_target']}字左右。")
        if outline.get("conflict"):
            user_parts.append(f"核心矛盾是{outline['conflict']}")
        if outline.get("excitement"):
            user_parts.append(f"爽点在{outline['excitement']}")
        if outline.get("hook"):
            user_parts.append(f"章末的悬念是{outline['hook']}")
        if outline.get("storyline"):
            user_parts.append(f"推进的故事线是{outline['storyline']}")
        if outline.get("foreshadowing"):
            user_parts.append(f"埋下的伏笔是{outline['foreshadowing']}")
        if outline.get("foreshadowing_payoff"):
            user_parts.append(f"回收的伏笔是{outline['foreshadowing_payoff']}")
    else:
        user_parts.append("请根据已有故事上下文，继续写出下一章内容。")

    user_parts.append("")
    user_parts.append("现在，直接写出本章正文。")

    user_prompt = "\n".join(user_parts)

    return system_prompt, user_prompt
