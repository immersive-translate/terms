import { load } from "https://deno.land/std@0.208.0/dotenv/mod.ts";
import { parse as parseYaml } from "https://deno.land/std@0.208.0/yaml/mod.ts";
import { ensureDir } from "https://deno.land/std@0.208.0/fs/mod.ts";

const languageMap: Record<string, string> = {
  "zh-CN": "简体中文",
  "zh-TW": "繁体中文",
  "en": "英文",
};

const targetLangs = ["zh-CN", "zh-TW", "en"];

interface MetaData {
  name: string;
  description: string;
  i18ns?: Record<string, { name: string; description: string }>;
}

async function translateMeta() {
  console.log("开始翻译任务...");

  // 确保dist目录存在
  await ensureDir("dist");
  console.log("已创建dist目录");

  // 复制所有glossary文件
  await copyGlossaryFiles();

  // 扫描meta目录下的所有yaml文件
  const metaDir = "meta";
  console.log(`正在扫描 ${metaDir} 目录...`);

  let fileCount = 0;
  for await (const entry of Deno.readDir(metaDir)) {
    if (entry.isFile && entry.name.endsWith(".yaml")) {
      console.log(`\n处理文件: ${entry.name}`);
      fileCount++;

      const content = await Deno.readTextFile(`${metaDir}/${entry.name}`);
      const data = parseYaml(content) as MetaData;
      console.log(
        `原始数据: name=${data.name}, description=${
          data.description?.substring(0, 30)
        }...`,
      );

      // 添加i18ns字段
      data.i18ns = {};

      // 获取源语言
      const sourceLang = detectLanguage(data.name);
      console.log(`检测到源语言: ${sourceLang}`);

      // 翻译name和description
      for (const lang of targetLangs) {
        console.log(`\n翻译到 ${lang}...`);
        if (lang === sourceLang) {
          console.log(`目标语言与源语言相同，跳过翻译`);
          data.i18ns[lang] = {
            name: data.name,
            description: data.description,
          };
        } else {
          try {
            console.log(`发送翻译请求...`);
            const { name: translatedName, description: translatedDesc } =
              await translateWithOpenAI(
                { title: data.name, description: data.description },
                lang,
              );
            console.log(`翻译成功: ${translatedName.substring(0, 30)}...`);

            data.i18ns[lang] = {
              name: translatedName,
              description: translatedDesc,
            };
          } catch (error) {
            console.error(`翻译失败: ${error.message}`);
            // 如果翻译失败，使用原文
            data.i18ns[lang] = {
              name: data.name,
              description: data.description,
            };
          }
        }
      }

      // 写入到dist目录
      const outputPath = `dist/${entry.name.replace(".yaml", ".json")}`;
      await Deno.writeTextFile(outputPath, JSON.stringify(data, null, 2));
      console.log(`已写入文件: ${outputPath}`);
    }
  }

  if (fileCount === 0) {
    console.warn(`警告: ${metaDir} 目录中没有找到.yaml文件`);
  } else {
    console.log(`\n完成! 共处理 ${fileCount} 个文件`);
  }
}

// 执行翻译并捕获顶层错误
try {
  await translateMeta();
} catch (error) {
  console.error("程序执行失败:", error);
  Deno.exit(1);
}

async function translateWithOpenAI(
  text: { title: string; description: string },
  targetLang: string,
) {
  console.log("准备发送翻译请求...");
  const env = await load();
  const apiKey = env["BASI_OPENAI_KEY"];
  if (!apiKey) {
    throw new Error("缺少 BASI_OPENAI_KEY 环境变量");
  }

  const myHeaders = new Headers();
  myHeaders.append("Authorization", "Bearer " + apiKey);
  myHeaders.append("Content-Type", "application/json");

  const targetLangName = languageMap[targetLang];
  if (!targetLangName) {
    throw new Error("不支持的目标语言: " + targetLang);
  }

  const payload = {
    title: text.title,
    description: text.description,
  };

  console.log(`请求内容: ${JSON.stringify(payload, null, 2)}`);

  const raw = JSON.stringify({
    "model": "gpt-4-0125-preview",
    "temperature": 0,
    "messages": [
      {
        "role": "system",
        "content":
          "你是一个专业的翻译引擎。请将输入的JSON对象准确翻译为目标语言，保持JSON结构不变，只翻译值部分。",
      },
      {
        "role": "user",
        "content": `请翻译为${targetLangName}，以JSON格式返回:\n${
          JSON.stringify(payload, null, 2)
        }`,
      },
    ],
  });

  const requestOptions: RequestInit = {
    method: "POST",
    headers: myHeaders,
    body: raw,
  };

  const apiBase = env["BASI_OPENAI_API"] ||
    "https://api.openai.com/v1/chat/completions";
  console.log(`使用API端点: ${apiBase}`);

  const res = await fetch(apiBase, requestOptions);
  const responseText = await res.text();

  if (res.ok) {
    console.log("收到API响应", responseText);
    const json = JSON.parse(responseText);
    const result = JSON.parse(json.choices[0].message.content);
    return {
      name: result.title,
      description: result.description,
    };
  } else {
    console.error(`API请求失败: ${res.status}`);
    throw new Error(res.status + ": " + responseText);
  }
}

async function copyGlossaryFiles() {
  const glossaryDir = "glossaries";
  const targetDir = "dist/glossaries";

  // 确保目标目录存在
  await ensureDir(targetDir);

  // 复制所有glossary文件
  for await (const entry of Deno.readDir(glossaryDir)) {
    if (entry.isFile) {
      const sourcePath = `${glossaryDir}/${entry.name}`;
      const targetPath = `${targetDir}/${entry.name}`;
      await Deno.copyFile(sourcePath, targetPath);
      console.log(`Copied ${entry.name} to dist/glossary/`);
    }
  }
}

function detectLanguage(text: string): string {
  // 简单判断是否包含中文字符
  if (/[\u4e00-\u9fa5]/.test(text)) {
    // 如果包含繁体特有字符，判定为繁体中文
    if (/[萬與醜專業叢東絲兩嚴喪個爿豐臨為麗舉愛練叢臺與]{1,}/.test(text)) {
      return "zh-TW";
    }
    return "zh-CN";
  }

  // 如果主要是英文字符
  if (/^[a-zA-Z0-9\s\p{P}]*$/u.test(text)) {
    return "en";
  }

  return "auto";
}
