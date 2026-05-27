import csv
import hashlib
import html
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "poe2_translation_glossary.csv"
OUTPUT = ROOT / "poe2_translation_glossary.csv"
CACHE_DIR = ROOT / ".cache_poe_glossary"

FIELDNAMES = [
    "source_term",
    "zh_CN",
    "zh_TW",
    "category",
    "usage_note",
    "source_url",
    "confidence",
]

POEDB_PAGES = [
    ("Currency_Exchange", "POE1 currency and fragments"),
    ("Items", "POE1 item classes"),
    ("Vendor_recipe_system", "POE1 vendor recipes"),
    ("Gem", "POE1 gems"),
    ("Skill_Gems", "POE1 active skill gems"),
    ("Support_Gems", "POE1 support gems"),
    ("Transfigured_Gems", "POE1 transfigured gems"),
    ("Exceptional", "POE1 exceptional gems"),
    ("Modifiers", "POE1 modifiers"),
    ("Oil", "POE1 oils and anointments"),
    ("Horticrafting", "POE1 harvest crafts"),
    ("Quest", "POE1 quests and areas"),
    ("Ascendancy_class", "POE1 classes and ascendancies"),
    ("Bloodline_Ascendancy_class", "POE1 bloodline ascendancies"),
    ("Maps", "POE1 maps"),
]

MANUAL_ROWS = [
    # Core POE1 classes and ascendancies.
    ("Path of Exile", "流放之路", "流亡黯道", "POE1 game title", "POE1 游戏名。", "https://www.poewiki.net/", "high"),
    ("PoE", "POE", "POE", "Abbreviation", "Path of Exile 的常用缩写。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Marauder", "野蛮人", "野蠻人", "POE1 class", "力量职业。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Duelist", "决斗者", "決鬥者", "POE1 class", "力量/敏捷职业。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Ranger", "游侠", "遊俠", "POE1 class", "敏捷职业。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Shadow", "暗影刺客", "暗影刺客", "POE1 class", "敏捷/智慧职业。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Witch", "女巫", "女巫", "POE1 class", "智慧职业。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Templar", "圣堂武僧", "聖堂武僧", "POE1 class", "力量/智慧职业。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Scion", "贵族", "貴族", "POE1 class", "混合职业。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Juggernaut", "勇士", "勇士", "POE1 ascendancy", "野蛮人升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Berserker", "暴徒", "暴徒", "POE1 ascendancy", "野蛮人升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Chieftain", "酋长", "酋長", "POE1 ascendancy", "野蛮人升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Slayer", "处刑者", "處刑者", "POE1 ascendancy", "决斗者升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Gladiator", "卫士", "衛士", "POE1 ascendancy", "决斗者升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Champion", "冠军", "冠軍", "POE1 ascendancy", "决斗者升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Deadeye", "锐眼", "銳眼", "POE1 ascendancy", "游侠升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Raider", "侠客", "俠客", "POE1 ascendancy", "游侠升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Pathfinder", "追猎者", "追獵者", "POE1 ascendancy", "游侠升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Assassin", "刺客", "刺客", "POE1 ascendancy", "暗影升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Saboteur", "破坏者", "破壞者", "POE1 ascendancy", "暗影升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Trickster", "欺诈师", "詐欺師", "POE1 ascendancy", "暗影升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Necromancer", "死灵师", "死靈師", "POE1 ascendancy", "女巫升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Occultist", "秘术家", "秘術家", "POE1 ascendancy", "女巫升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Elementalist", "元素使", "元素使", "POE1 ascendancy", "女巫升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Inquisitor", "判官", "判官", "POE1 ascendancy", "圣堂升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Hierophant", "圣宗", "聖宗", "POE1 ascendancy", "圣堂升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Guardian", "守护者", "守護者", "POE1 ascendancy", "圣堂升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    ("Ascendant", "升华使徒", "昇華使徒", "POE1 ascendancy", "贵族升华。", "https://poedb.tw/us/Ascendancy_class", "high"),
    # Major systems, mechanics, and stats.
    ("League", "赛季", "聯盟", "Game mode", "赛季/联盟机制语境中使用。", "https://www.poewiki.net/", "medium"),
    ("Challenge League", "挑战赛季", "挑戰聯盟", "Game mode", "定期更新的赛季环境。", "https://www.poewiki.net/", "medium"),
    ("Standard League", "标准赛季", "標準聯盟", "Game mode", "永久赛季环境。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Ruthless", "残酷模式", "殘酷模式", "Game mode", "资源更稀缺的特殊模式。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Private League", "私人赛季", "私人聯盟", "Game mode", "玩家创建的自定义赛季。", "https://www.poewiki.net/", "medium"),
    ("Item Level", "物品等级", "物品等級", "Item property", "社区常写 ilvl。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Gem Level", "宝石等级", "寶石等級", "Gem property", "社区常写 gem level。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Quality", "品质", "品質", "Item property", "物品或宝石品质；社区常写 Q。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Socket", "插槽", "插槽", "Item property", "装备插槽。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Linked Socket", "连接插槽", "連結插槽", "Item property", "社区常写 4L/5L/6L。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Red Socket", "红色插槽", "紅色插槽", "Item property", "力量宝石插槽。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Green Socket", "绿色插槽", "綠色插槽", "Item property", "敏捷宝石插槽。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Blue Socket", "蓝色插槽", "藍色插槽", "Item property", "智慧宝石插槽。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("White Socket", "白色插槽", "白色插槽", "Item property", "可放任意颜色宝石。", "https://www.poewiki.net/", "medium"),
    ("Mirrored", "已复制", "已複製", "Item property", "由魔镜复制或相关机制生成，不能再修改。", "https://poedb.tw/us/Currency_Exchange", "medium"),
    ("Fractured", "破裂", "破裂", "Item property", "固定一条词缀的物品状态。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Synthesised", "忆境", "追憶", "Item property", "Synthesis 相关物品状态；简中项目内需统一。", "https://poedb.tw/us/Modifiers", "low"),
    ("Influenced Item", "势力物品", "勢力物品", "Item property", "塑界者、裂界者、征服者等影响。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Shaper Item", "塑界者物品", "塑界者物品", "Item property", "Shaper 势力。", "https://poedb.tw/us/Modifiers", "high"),
    ("Elder Item", "裂界者物品", "尊師物品", "Item property", "Elder 势力；繁中也常见尊师。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Crusader Item", "圣战者物品", "聖戰士物品", "Item property", "Conqueror 势力。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Hunter Item", "狩猎者物品", "狩獵者物品", "Item property", "Conqueror 势力。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Redeemer Item", "救赎者物品", "救贖者物品", "Item property", "Conqueror 势力。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Warlord Item", "督军物品", "總督軍物品", "Item property", "Conqueror 势力。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Frenzy Charge", "狂怒球", "狂怒球", "Charge", "三色球之一。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Power Charge", "暴击球", "暴擊球", "Charge", "三色球之一。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Endurance Charge", "耐力球", "耐力球", "Charge", "三色球之一。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Inspiration Charge", "启迪球", "啟發球", "Charge", "辅助宝石相关。", "https://poedb.tw/us/Support_Gems", "medium"),
    ("Virulence", "毒力", "毒性", "Charge", "苦痛之捷相关层数。", "https://poedb.tw/us/Skill_Gems", "medium"),
    ("Life Leech", "生命偷取", "生命偷取", "Recovery", "从伤害中回复生命。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Mana Leech", "魔力偷取", "魔力偷取", "Recovery", "从伤害中回复魔力。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Energy Shield Leech", "能量护盾偷取", "能量護盾偷取", "Recovery", "从伤害中回复能量护盾。", "https://www.poewiki.net/", "medium"),
    ("Regeneration", "再生", "再生", "Recovery", "持续回复资源。", "https://poedb.tw/us/Modifiers", "high"),
    ("Recharge", "充能回复", "充能恢復", "Recovery", "能量护盾自动回复机制。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Recovery", "回复", "恢復", "Recovery", "资源回复总称。", "https://poedb.tw/us/Modifiers", "high"),
    ("Recoup", "补偿回复", "補償恢復", "Recovery", "承受伤害后一段时间返还资源。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Spell Suppression", "法术压制", "法術壓抑", "Defence", "降低法术击中伤害的防御属性。", "https://poedb.tw/us/Modifiers", "high"),
    ("Ward", "结界", "護佑", "Defence", "远征后加入的防御资源；简中项目内需统一。", "https://poedb.tw/us/Modifiers", "low"),
    ("Fortify", "护体", "護體", "Defence", "承受击中伤害减免效果。", "https://poedb.tw/us/Modifiers", "high"),
    ("Fortification", "护体层数", "護體層數", "Defence", "Fortify 的层数。", "https://poedb.tw/us/Modifiers", "high"),
    ("Stun", "眩晕", "暈眩", "Crowd control", "使目标短暂无法行动。", "https://poedb.tw/us/Modifiers", "high"),
    ("Freeze", "冻结", "冰凍", "Ailment", "冰冷异常。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Brittle", "脆弱", "易碎", "Alternative ailment", "替代冰冷异常。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Scorch", "灼烧", "焦灼", "Alternative ailment", "替代火焰异常。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Sap", "精疲力尽", "疲憊", "Alternative ailment", "替代闪电异常。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "low"),
    ("Corrupted Blood", "腐化之血", "腐化之血", "Ailment", "可叠加的流血类减益；社区缩写 CB。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Maim", "瘫痪", "癱瘓", "Debuff", "降低移动速度的物理相关减益。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Hinder", "缓速", "阻礙", "Debuff", "降低移动速度的减益。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Intimidate", "威吓", "威嚇", "Debuff", "使目标承受更多攻击伤害。", "https://poedb.tw/us/Modifiers", "high"),
    ("Unnerve", "胆怯", "膽怯", "Debuff", "使目标承受更多法术伤害。", "https://poedb.tw/us/Modifiers", "high"),
    ("Withered", "凋零", "凋零", "Debuff", "提高承受混沌伤害的减益。", "https://poedb.tw/us/Modifiers", "high"),
    ("Covered in Ash", "被灰烬缠身", "被灰燼纏身", "Debuff", "常见火焰相关减益。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Elemental Damage", "元素伤害", "元素傷害", "Damage type", "火焰、冰冷/冰霜、闪电总称。", "https://poedb.tw/us/Modifiers", "high"),
    ("Damage over Time", "持续伤害", "持續傷害", "Damage", "社区常写 DoT。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("Hit", "击中", "擊中", "Combat", "一次直接命中。", "https://poedb.tw/us/Modifiers", "high"),
    ("Critical Strike Chance", "暴击率", "暴擊率", "Combat", "造成暴击的概率。", "https://poedb.tw/us/Modifiers", "high"),
    ("Critical Strike Multiplier", "暴击伤害加成", "暴擊加成", "Combat", "暴击伤害倍率。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Penetration", "穿透抗性", "穿透抗性", "Combat", "伤害计算时无视部分抗性。", "https://poedb.tw/us/Modifiers", "high"),
    ("Conversion", "伤害转换", "傷害轉換", "Combat", "将一种伤害转换为另一种。", "https://poedb.tw/us/Modifiers", "high"),
    ("Gain as Extra", "获得额外", "獲得額外", "Combat", "按某种伤害获得额外另一种伤害。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Increased", "提高", "增加", "Stat wording", "与 reduced 加算。", "https://poedb.tw/us/Modifiers", "high"),
    ("Reduced", "降低", "減少", "Stat wording", "与 increased 加算。", "https://poedb.tw/us/Modifiers", "high"),
    ("More", "总增", "更多", "Stat wording", "乘算增益；翻译时需按句子自然处理。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Less", "总降", "更少", "Stat wording", "乘算减益；翻译时需按句子自然处理。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Additional", "附加", "附加", "Stat wording", "通常用于附加点伤。", "https://poedb.tw/us/Modifiers", "high"),
    ("Nearby", "周围", "附近", "Stat wording", "POE 中 nearby 没有固定距离，按上下文。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Recently", "近期内", "近期內", "Stat wording", "通常指过去 4 秒。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Low Life", "低血", "低血量", "Condition", "生命低于阈值的状态。", "https://poedb.tw/us/Modifiers", "high"),
    ("Full Life", "满血", "滿血", "Condition", "生命全满状态。", "https://poedb.tw/us/Modifiers", "high"),
    ("Low Mana", "低魔", "低魔力", "Condition", "魔力低于阈值的状态。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Full Energy Shield", "满能量护盾", "滿能量護盾", "Condition", "能量护盾全满状态。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Onslaught", "猛攻", "猛攻", "Buff", "提高攻击、施法和移动速度。", "https://poedb.tw/us/Modifiers", "high"),
    ("Phasing", "迷踪", "迷蹤", "Buff", "可穿越敌人。", "https://poedb.tw/us/Modifiers", "high"),
    ("Arcane Surge", "秘术增强", "秘能波動", "Buff", "法术相关增益；简中项目内需统一。", "https://poedb.tw/us/Modifiers", "low"),
    ("Tailwind", "提速尾流", "順風", "Buff", "锐眼相关速度增益；简中项目内需统一。", "https://poedb.tw/us/Modifiers", "low"),
    ("Elusive", "灵巧", "靈巧", "Buff", "提供防御/移动相关收益。", "https://poedb.tw/us/Modifiers", "high"),
    ("Adrenaline", "肾上腺素", "腎上腺素", "Buff", "强力临时增益。", "https://poedb.tw/us/Modifiers", "high"),
    ("Rampage", "暴怒", "暴怒", "Buff", "连杀奖励机制。", "https://poedb.tw/us/Modifiers", "medium"),
    ("Brand", "烙印", "烙印", "Skill tag", "附着敌人的法术类型。", "https://poedb.tw/us/Skill_Gems", "high"),
    ("Warcry", "战吼", "戰吼", "Skill tag", "技能标签。", "https://poedb.tw/us/Skill_Gems", "high"),
    ("Channelling", "吟唱", "引導", "Skill tag", "持续引导施放技能。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Travel", "位移", "位移", "Skill tag", "移动技能标签。", "https://poedb.tw/us/Skill_Gems", "medium"),
    ("Mine", "地雷", "地雷", "Skill tag", "代理施放技能。", "https://poedb.tw/us/Skill_Gems", "high"),
    ("Herald", "捷", "捷", "Skill tag", "保留型增益技能类别。", "https://poedb.tw/us/Skill_Gems", "medium"),
    ("Banner", "旗帜", "旗幟", "Skill tag", "保留/放置型技能类别。", "https://poedb.tw/us/Skill_Gems", "medium"),
    ("Guard Skill", "防护技能", "防護技能", "Skill tag", "防御型瞬发技能类别。", "https://poedb.tw/us/Skill_Gems", "medium"),
    ("Vaal Skill", "瓦尔技能", "瓦爾技能", "Skill tag", "消耗灵魂使用的技能。", "https://poedb.tw/us/Skill_Gems", "high"),
    # Leagues and league mechanics.
    ("Abyss", "深渊", "深淵", "League mechanic", "POE1 联盟/机制。", "https://poedb.tw/us/Items", "high"),
    ("Bestiary", "野兽", "獸獵", "League mechanic", "POE1 联盟/机制；简中也可译兽猎。", "https://poedb.tw/us/Items", "medium"),
    ("Incursion", "穿越", "穿越", "League mechanic", "POE1 联盟/机制。", "https://poedb.tw/us/Items", "high"),
    ("Delve", "掘狱", "掘獄", "League mechanic", "POE1 联盟/机制。", "https://poedb.tw/us/Items", "high"),
    ("Betrayal", "背叛", "反叛", "League mechanic", "POE1 联盟/机制。", "https://www.poe2db.info/en/glossary", "medium"),
    ("Synthesis", "忆境", "追憶", "League mechanic", "POE1 联盟/机制；简中项目内需统一。", "https://poedb.tw/us/Items", "low"),
    ("Legion", "军团", "戰亂", "League mechanic", "POE1 联盟/机制。", "https://poedb.tw/us/Items", "medium"),
    ("Blight", "枯疫", "凋落", "League mechanic", "POE1/POE2 机制；简中项目内需统一。", "https://www.poe2db.info/en/glossary", "low"),
    ("Metamorph", "菌潮", "魔物園", "League mechanic", "POE1 联盟/机制；不同中文社区译名差异较大，需复核。", "https://poedb.tw/us/Items", "low"),
    ("Delirium", "谵妄", "譫妄", "League mechanic", "POE1/POE2 机制。", "https://poedb.tw/us/Items", "high"),
    ("Harvest", "丰收", "豐收", "League mechanic", "POE1/POE2 机制。", "https://www.poe2db.info/en/glossary", "medium"),
    ("Heist", "夺宝", "劫盜", "League mechanic", "POE1 机制。", "https://poedb.tw/us/Items", "high"),
    ("Ritual", "祭祀", "祭祀", "League mechanic", "POE1/POE2 机制。", "https://poedb.tw/us/Items", "high"),
    ("Ultimatum", "最后通牒", "最後通牒", "League mechanic", "POE1/POE2 机制。", "https://www.poe2wiki.net/wiki/Guide%3ACommunity_shorthand", "medium"),
    ("Expedition", "先祖秘藏", "探險", "League mechanic", "POE1 机制；简中项目内需统一。", "https://poedb.tw/us/Items", "low"),
    ("Scourge", "灾魇", "災魘", "League mechanic", "POE1 机制。", "https://poedb.tw/us/Items", "medium"),
    ("Archnemesis", "宿敌", "宿敵", "League mechanic", "POE1 机制。", "https://poedb.tw/us/Items", "high"),
    ("Sentinel", "哨兵", "守望", "League mechanic", "POE1 机制；简中项目内需统一。", "https://poedb.tw/us/Items", "low"),
    ("Lake of Kalandra", "卡兰德迷湖", "卡蘭德迷湖", "League mechanic", "POE1 联盟。", "https://poedb.tw/us/Items", "medium"),
    ("Sanctum", "圣所", "聖域", "League mechanic", "POE1/POE2 类似机制。", "https://www.poe2wiki.net/wiki/Guide%3ACommunity_shorthand", "medium"),
    ("Crucible", "熔炉", "熔火冥獄", "League mechanic", "POE1 联盟；简中项目内需统一。", "https://poedb.tw/us/Items", "low"),
    ("Ancestor", "先祖", "祖靈", "League mechanic", "POE1 联盟/机制。", "https://poedb.tw/us/Items", "medium"),
    ("Affliction", "苦痛", "苦痛", "League mechanic", "POE1 联盟。", "https://poedb.tw/us/Items", "medium"),
    ("Necropolis", "死寂亡城", "死境", "League mechanic", "POE1 联盟；简中项目内需统一。", "https://poedb.tw/us/Items", "low"),
    ("Settlers of Kalguur", "卡尔葛拓荒者", "卡爾葛拓荒者", "League mechanic", "POE1 联盟。", "https://poedb.tw/us/Currency_Exchange", "medium"),
    # Community shorthand rows. Keep the acronym unchanged in target, with the meaning in notes.
    ("AA", "AA", "AA", "Community shorthand", "Arctic Armour。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("AG", "AG", "AG", "Community shorthand", "Animate Guardian。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Alch", "点金", "鍊金", "Community shorthand", "Orb of Alchemy 或使用点金石。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Alt", "改造", "改造", "Community shorthand", "Orb of Alteration 或使用改造石。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Ammy", "项链", "項鍊", "Community shorthand", "Amulet。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("AoF", "火之化身", "火之化身", "Community shorthand", "Avatar of Fire。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("AW", "幻化武器", "幻化武器", "Community shorthand", "Animate Weapon。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("BAMA", "BAMA", "BAMA", "Community shorthand", "Blink Arrow/Mirror Arrow 构筑简称。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "low"),
    ("BB", "飞刃风暴/刀爆", "刀鋒爆破", "Community shorthand", "Blade Blast；简中社区译名需按项目统一。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "low"),
    ("BF", "刀雨/刀刃乱舞", "刀雨/刀鋒亂舞", "Community shorthand", "Bladefall 或 Blade Flurry，需按上下文。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "low"),
    ("BM", "血魔法", "血魔法", "Community shorthand", "POE1 指 Blood Magic；POE2 中可能指 Blood Mage。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("BoR", "祭礼之雨", "祭禮之雨", "Community shorthand", "The Bringer of Rain。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("BR", "鲜血狂怒", "鮮血狂怒", "Community shorthand", "Blood Rage。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("BV", "飞刃风暴", "飛刃風暴", "Community shorthand", "Blade Vortex。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CA", "腐蚀箭矢", "腐蝕箭矢", "Community shorthand", "Caustic Arrow。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CB", "腐化之血", "腐化之血", "Community shorthand", "Corrupted Blood。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("CF", "腐化潮", "腐化潮", "Community shorthand", "Corrupting Fever。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CI", "异灵之体", "異靈之體", "Community shorthand", "Chaos Inoculation。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CoC", "暴击时施放", "暴擊時施放", "Community shorthand", "Cast On Critical Strike。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("CoD", "死亡时施放", "死亡時施放", "Community shorthand", "Cast on Death。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CoH", "击中附加诅咒", "擊中附加詛咒", "Community shorthand", "旧称 Curse on Hit；现多指 Hextouch。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CoMK", "近战击败时施放", "近戰擊殺時施放", "Community shorthand", "Cast on Melee Kill。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("Conc", "集中效应", "集中效應", "Community shorthand", "Concentrated Effect。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CwC", "吟唱时施放", "引導時施放", "Community shorthand", "Cast while Channelling。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("CwDT", "受伤时施放", "受傷時施放", "Community shorthand", "Cast when Damage Taken。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("CwS", "被晕眩时施放", "被暈眩時施放", "Community shorthand", "Cast when Stunned。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("DoT", "持续伤害", "持續傷害", "Community shorthand", "Damage over Time。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("DPS", "每秒伤害", "每秒傷害", "Community shorthand", "Damage per Second。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("EO", "元素超载", "元素超載", "Community shorthand", "Elemental Overload。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("EE", "元素之相", "元素之相", "Community shorthand", "Elemental Equilibrium。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("ES", "能量护盾", "能量護盾", "Community shorthand", "Energy Shield。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("GGG", "GGG", "GGG", "Community shorthand", "Grinding Gear Games。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("HoA", "苦痛之捷/灰烬之捷", "苦痛之捷/灰燼之捷", "Community shorthand", "Herald of Agony 或 Herald of Ash，需按上下文。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "low"),
    ("HoI", "冰霜之捷", "冰霜之捷", "Community shorthand", "Herald of Ice。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("HoT", "闪电之捷", "閃電之捷", "Community shorthand", "Herald of Thunder。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("IC", "不朽怒嚎", "不朽怒嚎", "Community shorthand", "Immortal Call。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("IR", "霸体", "霸體", "Community shorthand", "Iron Reflexes。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("LL", "低血/生命偷取", "低血/生命偷取", "Community shorthand", "Low Life 或 Life Leech，需按上下文。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "low"),
    ("MoM", "心灵升华", "心靈昇華", "Community shorthand", "Mind Over Matter。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("MS", "移动速度", "移動速度", "Community shorthand", "Movement Speed。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("RF", "正义之火", "正義之火", "Community shorthand", "Righteous Fire。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("RT", "必中", "必中", "Community shorthand", "Resolute Technique。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("SC", "普通模式/标准", "標準模式/標準", "Community shorthand", "Softcore 或 Standard League，需按上下文。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
    ("SSF", "独狼自给", "獨狼自給", "Community shorthand", "Solo Self-Found。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "high"),
    ("ST", "灵体投掷/单体", "靈體投擲/單體", "Community shorthand", "Spectral Throw 或 Single Target，需按上下文。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "low"),
    ("VP", "瓦尔冥约", "瓦爾冥約", "Community shorthand", "Vaal Pact。", "https://www.poewiki.net/wiki/Guide:Community_shorthand", "medium"),
]


class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attrs = dict(attrs)
        href = attrs.get("href")
        if href:
            self.current = {"href": href, "text": []}

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            text = clean_text("".join(self.current["text"]))
            if text:
                self.links.append((self.current["href"], text))
            self.current = None


def clean_text(value):
    value = html.unescape(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def cache_path(url):
    return CACHE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".html")


def fetch(url):
    CACHE_DIR.mkdir(exist_ok=True)
    path = cache_path(url)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; Codex glossary builder)",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        text = response.read().decode("utf-8", "replace")
    path.write_text(text, encoding="utf-8")
    time.sleep(0.25)
    return text


def normalize_href(href):
    href = href.split("#", 1)[0].split("?", 1)[0]
    href = href.rstrip("/")
    href = re.sub(r"^https?://(?:www\.)?poedb\.tw", "", href)
    href = re.sub(r"^/(us|cn|tw)/?", "", href)
    if not href:
        return ""
    if href.startswith(("http:", "https:", "mailto:", "javascript:", "#")):
        return ""
    if href.startswith(("/", "../")):
        return ""
    return href


EXCLUDE_TEXT = {
    "PoEDB",
    "Patreon",
    "English",
    "简体中文",
    "繁體中文",
    "TW 繁體中文",
    "CN 简体中文",
    "US English",
    "Deutsch",
    "Français",
    "Português",
    "Русский",
    "Español",
    "한국어",
    "日本語",
    "ไทย",
    "Privacy Policy",
    "Terms of Service",
    "Back to Top",
    "Version",
    "Item",
    "Items",
}


def is_source_term(text):
    if not text or text in EXCLUDE_TEXT:
        return False
    if len(text) > 80:
        return False
    if not re.search(r"[A-Za-z]", text):
        return False
    if re.search(r"(Requires Level|Stack Size|Place into|Right click|Cost:|Level: \(|Cooldown Time)", text):
        return False
    if text.count(" ") > 8:
        return False
    if re.match(r"^[\d\s.,:+%()-]+$", text):
        return False
    return True


def is_target_term(text):
    if not text or text in EXCLUDE_TEXT:
        return False
    if len(text) > 100:
        return False
    if re.search(r"(Requires Level|Stack Size|Place into|Right click|Cost:|Level: \(|Cooldown Time)", text):
        return False
    if text.count(" ") > 10:
        return False
    return True


def extract_link_map(url):
    parser = LinkExtractor()
    parser.feed(fetch(url))
    result = {}
    for href, text in parser.links:
        key = normalize_href(href)
        if not key:
            continue
        if key not in result or len(text) < len(result[key]):
            result[key] = text
    return result


def make_row(source, zh_cn, zh_tw, category, note, source_url, confidence):
    return {
        "source_term": clean_text(source),
        "zh_CN": clean_text(zh_cn),
        "zh_TW": clean_text(zh_tw),
        "category": clean_text(category),
        "usage_note": clean_text(note),
        "source_url": clean_text(source_url),
        "confidence": clean_text(confidence),
    }


def load_existing():
    rows = []
    if not INPUT.exists():
        return rows
    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("source_term"):
                rows.append({name: clean_text(row.get(name, "")) for name in FIELDNAMES})
    return rows


def add_row(rows_by_key, row):
    if not row["source_term"] or not row["zh_CN"]:
        return
    key = row["source_term"].casefold()
    existing = rows_by_key.get(key)
    if not existing:
        rows_by_key[key] = row
        return
    # Prefer hand-curated/high confidence rows, but fill blanks from scraped rows.
    rank = {"low": 1, "medium": 2, "high": 3}
    if rank.get(row["confidence"], 0) > rank.get(existing["confidence"], 0):
        merged = existing.copy()
        merged.update({k: v for k, v in row.items() if v})
        rows_by_key[key] = merged
    else:
        for field in ("zh_CN", "zh_TW", "category", "usage_note", "source_url"):
            if not existing.get(field) and row.get(field):
                existing[field] = row[field]


def scrape_poedb_rows():
    rows = []
    for page, category in POEDB_PAGES:
        maps = {}
        for lang in ("us", "cn", "tw"):
            url = f"https://poedb.tw/{lang}/{page}"
            try:
                maps[lang] = extract_link_map(url)
            except (urllib.error.URLError, TimeoutError) as exc:
                print(f"warn: failed {url}: {exc}", file=sys.stderr)
                maps[lang] = {}

        source_url = f"https://poedb.tw/us/{page}"
        for key, source in maps["us"].items():
            if not is_source_term(source):
                continue
            zh_cn = maps["cn"].get(key, "")
            zh_tw = maps["tw"].get(key, "")
            if not is_target_term(zh_cn):
                continue
            if not is_target_term(zh_tw):
                zh_tw = zh_cn
            if source == zh_cn and source == zh_tw and len(source) > 24:
                continue
            rows.append(
                make_row(
                    source,
                    zh_cn,
                    zh_tw,
                    category,
                    f"Scraped from paired PoEDB POE1 pages; key={key}.",
                    source_url,
                    "medium",
                )
            )
    return rows


def main():
    rows_by_key = {}
    for row in load_existing():
        add_row(rows_by_key, row)

    for values in MANUAL_ROWS:
        add_row(rows_by_key, make_row(*values))

    scraped = scrape_poedb_rows()
    for row in scraped:
        add_row(rows_by_key, row)

    rows = sorted(rows_by_key.values(), key=lambda r: (r["category"].lower(), r["source_term"].lower()))
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"existing+manual+scraped rows: {len(rows)}")
    print(f"scraped candidate rows: {len(scraped)}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
