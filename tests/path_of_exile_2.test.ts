import {
    assert,
    assertEquals,
} from "https://deno.land/std@0.220.1/assert/mod.ts";
import { parse } from "https://deno.land/std@0.220.1/csv/parse.ts";
import { describe, it } from "https://deno.land/std@0.220.1/testing/bdd.ts";

const glossaries = await Promise.all(["en", "zh-CN"].map(async (language) => {
    const bytes = await Deno.readFile(
        new URL(`../glossaries/path-of-exile-2_${language}.csv`, import.meta.url),
    );
    const rows = parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    return { language, bytes, rows };
}));
const sources = glossaries.find(({ language }) => language === "zh-CN")!.rows
    .slice(1).map((row) => row[0]);

// 按维护者说明模拟匹配：不区分大小写，也不要求单词边界。
function matchTerms(text: string): string[] {
    const lowerText = text.toLowerCase();
    return sources.filter((source) => lowerText.includes(source.toLowerCase()));
}

describe("PoE2 术语库结构", () => {
    for (const { language, bytes, rows } of glossaries) {
        it(`${language} 使用无 BOM 的 UTF-8、精确三列和非空词条`, () => {
            assert(!(bytes[0] === 0xEF && bytes[1] === 0xBB && bytes[2] === 0xBF),
                "CSV 不能包含 UTF-8 BOM");
            assertEquals(rows[0], ["source", "target", "tgt_lng"]);
            assert(rows.length > 1);
            for (const [index, row] of rows.slice(1).entries()) {
                assertEquals(row.length, 3, `CSV 第 ${index + 2} 行列数错误`);
                assert(row.every((cell) => cell.trim().length > 0),
                    `CSV 第 ${index + 2} 行包含空字段`);
                assertEquals(row[2], language, `CSV 第 ${index + 2} 行语言错误`);
            }
        });

        it(`${language} source 在不区分大小写时仍唯一`, () => {
            const sources = rows.slice(1).map((row) => row[0].toLowerCase());
            assertEquals(new Set(sources).size, sources.length);
        });
    }

    it("保留双向语言元数据和唯一的公开索引入口", async () => {
        const [metaText, indexText] = await Promise.all([
            Deno.readTextFile(new URL("../meta/path-of-exile-2.json", import.meta.url)),
            Deno.readTextFile(new URL("../meta/index.json", import.meta.url)),
        ]);
        const meta = JSON.parse(metaText);
        const index = JSON.parse(indexText);
        assertEquals(meta.id, "path-of-exile-2");
        assertEquals(meta.glossary, "path-of-exile-2");
        assertEquals(new Set(meta.langs), new Set(["en", "zh-CN"]));
        assert(meta.langs.every((language: string) => meta.i18ns[language]));
        assertEquals(index.filter((id: string) => id === "path-of-exile-2").length, 1);
    });

    it("不添加未经审核的三字符及以下术语", () => {
        // AoE 是明确的范围机制缩写，保留为短词例外。
        assertEquals(sources.filter((source) => source.length <= 3), ["AoE"]);
    });
});

describe("PoE2 子串匹配回归", () => {
    const ordinaryWords: Array<[string, string[]]> = [
        ["International", []],
        ["characters", []],
        ["action", []],
        ["search", []],
        ["scripts", []],
        ["descriptions", []],
        ["streamers", []],
        ["index", []],
        ["absorb", []],
        ["hospital", []],
        ["import", []],
        ["metadata", []],
        ["market", []],
        ["blink", []],
        ["window", []],
    ];

    for (const [text, expected] of ordinaryWords) {
        it(`普通英文 ${text} 不触发歧义子串`, () => {
            assertEquals(matchTerms(text), expected);
        });
    }

    const explicitTerms = [
        "AoE", "Act 1", "Act 2", "Act 3", "Act 4", "Str/Dex", "Str/Int",
        "Dex/Int", "Str/Dex/Int", "Vaal", "Orb of Augmentation", "Fireball",
        "Meta Gems", "Wind Skills", "Orb Skills", "Chaos Orb", "Skill Gems",
        "Andvarius", "Astramentis",
    ];
    for (const source of explicitTerms) {
        it(`保留明确术语 ${source} 并允许大小写变化`, () => {
            assert(sources.includes(source), `缺少明确术语 ${source}`);
            assert(matchTerms(source.toUpperCase()).includes(source));
            assert(matchTerms(source.toLowerCase()).includes(source));
        });
    }
});

const substringCases: Record<string, string> = JSON.parse(
    await Deno.readTextFile(
        new URL("./fixtures/path_of_exile_2_substring_cases.json", import.meta.url),
    ),
);
assert(Object.keys(substringCases).length > 0, "子串反例集不能为空");
describe("PoE2 已审核歧义词条回归", () => {
    for (const [source, witness] of Object.entries(substringCases)) {
        it(`${source} 不命中反例 ${witness}`, () => {
            assert(witness.toLowerCase().includes(source.toLowerCase()),
                `反例 ${witness} 必须包含 ${source} 的子串`);
            for (const text of [witness, witness.toLowerCase(), witness.toUpperCase()]) {
                assert(!matchTerms(text).some((term) =>
                    term.toLowerCase() === source.toLowerCase()),
                    `${source} 错误命中 ${text}`);
            }
        });
    }
});
