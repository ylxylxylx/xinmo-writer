export const writers = [
  {
    id: "xiong-mo",
    name: "墨寒",
    avatar: "🐺",
    style: "冷峻硬核",
    description: "擅长末日、废土、生存题材。文风冷峻克制，节奏快，动作描写扎实，对话精炼有力。",
    genres: ["末日", "废土", "科幻", "生存"],
    config: {
      writing_rules: "文风冷峻克制，禁止无意义抒情\n动作场景用短句快节奏，每句不超过15字\n对话不超过3句一组，穿插动作\n开篇直入冲突，不铺垫不寒暄",
      behavior_locks: "所有角色/不煽情不矫情，情绪通过动作和环境表达",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 2, max_inner_sentences: 2 }
    }
  },
  {
    id: "shui-yue",
    name: "水月",
    avatar: "🌙",
    style: "细腻温婉",
    description: "擅长言情、古代、宫廷题材。文笔细腻，情感描写深入，擅长营造氛围和心理刻画。",
    genres: ["言情", "古代", "宫廷", "都市"],
    config: {
      writing_rules: "情感描写要含蓄，用细节传递而非直说\n环境描写要有情绪映射（景随情移）\n对话要有潜台词，不在嘴边的话更重要",
      behavior_locks: "主角/不为爱情放弃底线和尊严",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 4, max_inner_sentences: 4 }
    }
  },
  {
    id: "po-feng",
    name: "破风",
    avatar: "⚡",
    style: "热血爽快",
    description: "擅长玄幻、修仙、都市异能。节奏极快，爽点密集，擅长打脸和升级的爽感设计。",
    genres: ["玄幻", "修仙", "都市异能", "系统"],
    config: {
      writing_rules: "每章至少一个爽点或转折，不能连续平淡\n打脸场景要写全：对手嚣张→主角出手→围观震惊→对手后悔\n升级/突破场景要有仪式感",
      behavior_locks: "主角/不圣母，不妇人之仁\n反派/被打脸后要有合理的后续反应",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 2, max_inner_sentences: 2 }
    }
  },
  {
    id: "qiu-shui",
    name: "秋水",
    avatar: "🍂",
    style: "悬疑烧脑",
    description: "擅长悬疑、推理、恐怖题材。擅长设伏笔和线索，节奏控制精准，擅长营造紧张氛围。",
    genres: ["悬疑", "推理", "恐怖", "惊悚"],
    config: {
      writing_rules: "每章至少埋一条伏笔或回收一条伏笔\n线索要公平呈现，不能事后补设定\n恐惧来自未知，不直接描写恐怖画面\n章末必须是悬念断章",
      behavior_locks: "所有角色/不主动暴露关键信息（除非有合理动机）\n作者/禁止在正文中暗示凶手身份",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 3, max_inner_sentences: 3 }
    }
  },
  {
    id: "yun-fei",
    name: "云飞",
    avatar: "☁️",
    style: "轻松幽默",
    description: "擅长都市、日常、轻喜剧。文风轻松，对话有趣，擅长搞笑桥段和日常生活的趣味描写。",
    genres: ["都市", "日常", "轻喜剧", "校园"],
    config: {
      writing_rules: "对话要有梗，每段对话后可以跟一句吐槽或内心OS\n搞笑节奏：铺垫→反差→吐槽，三拍子\n严肃场景不能持续超过500字，必须穿插轻松元素",
      behavior_locks: "主角/可以吐槽但不能刻薄",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 2, max_inner_sentences: 3 }
    }
  },
  {
    id: "long-ling",
    name: "龙鳞",
    avatar: "🐉",
    style: "史诗大气",
    description: "擅长历史、权谋、战争题材。文风大气磅礴，擅长群像描写和宏大场景，节奏沉稳有力。",
    genres: ["历史", "权谋", "战争", "架空"],
    config: {
      writing_rules: "场景描写要有画面感，像镜头语言一样推进\n多人场景要有层次，不能流水账\n权谋博弈要有信息差，读者要能跟上逻辑\n战争场面要有全局视角和局部细节交替",
      behavior_locks: "所有角色/行为必须有合理动机，不能为剧情强行行动",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 5, max_inner_sentences: 3 }
    }
  },
  {
    id: "su-qing",
    name: "苏青",
    avatar: "🌸",
    style: "甜宠治愈",
    description: "擅长甜宠、治愈、轻松恋爱。擅长甜蜜互动和温馨日常，让读者会心一笑。",
    genres: ["甜宠", "治愈", "恋爱", "日常"],
    config: {
      writing_rules: "甜宠互动要有心动感，描写要细腻但不腻\n每个甜蜜场景后可以跟一点小虐或误会增加张力\n角色互动要有化学反应，不能只有对话",
      behavior_locks: "主角/不恋爱脑到失去自我",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 2, max_inner_sentences: 3 }
    }
  },
  {
    id: "ye-feng",
    name: "夜风",
    avatar: "🌑",
    style: "黑暗写实",
    description: "擅长犯罪、现实主义、社会题材。文风压抑写实，擅长人性刻画和道德困境。",
    genres: ["犯罪", "现实主义", "社会", "人性"],
    config: {
      writing_rules: "不做道德审判，让读者自己判断角色行为\n现实逻辑优先，不开金手指\n灰色地带的角色最有魅力，不要非黑即白\n结局不必圆满，合理即可",
      behavior_locks: "作者/禁止在正文中评判角色对错\n所有角色/行为要符合其所处环境和立场",
      prohibited_words: "",
      advanced: { natural_dialogue: true, no_useless_details: true, max_env_sentences: 3, max_inner_sentences: 4 }
    }
  }
]
