param(
    [string]$OutputPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "glossaries/wuthering-waves_zh-CN.csv")
)

$ErrorActionPreference = "Stop"
$baseUrl = "https://wuthering.gg"
$headers = @{
    "Accept-Language" = "en-US,en;q=0.9"
    "User-Agent" = "immersive-translate-terms/1.0 (Wuthering Waves glossary generator)"
}
$pages = @("characters", "weapons", "echos", "items")
$entityPages = @("characters", "weapons", "echos")

$curatedTerms = [ordered]@{
    "Wuthering Waves" = "鸣潮"
    "Resonator" = "共鸣者"
    "Resonance" = "共鸣"
    "Tacet Discord" = "残象"
    "Tacet Field" = "无音区"
    "Echo" = "声骸"
    "Echo Skill" = "声骸技能"
    "Sonata Effect" = "合鸣效果"
    "Data Bank" = "数据坞"
    "Basic Attack" = "普攻"
    "Heavy Attack" = "重击"
    "Mid-Air Attack" = "空中攻击"
    "Dodge Counter" = "闪避反击"
    "Resonance Skill" = "共鸣技能"
    "Resonance Liberation" = "共鸣解放"
    "Forte Circuit" = "共鸣回路"
    "Intro Skill" = "变奏技能"
    "Outro Skill" = "延奏技能"
    "Inherent Skill" = "固有技能"
    "Resonance Chain" = "共鸣链"
    "Concerto Energy" = "协奏能量"
    "Resonance Energy" = "共鸣能量"
    "ATK" = "攻击"
    "DEF" = "防御"
    "HP" = "生命"
    "Crit. Rate" = "暴击"
    "Crit. DMG" = "暴击伤害"
    "Energy Regen" = "共鸣效率"
    "Healing Bonus" = "治疗效果加成"
}

function Get-PageHtml {
    param(
        [string]$LocalePath,
        [string]$Page
    )

    $uri = "$baseUrl$LocalePath/$Page"
    Write-Host "Reading $uri"
    (Invoke-WebRequest -Method Get -Uri $uri -Headers $headers).Content
}

function Get-AttributeValue {
    param(
        [string]$Tag,
        [string]$Name
    )

    $match = [regex]::Match(
        $Tag,
        "(?:^|\s)$([regex]::Escape($Name))=`"(?<value>[^`"]*)`"",
        [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
    )
    if ($match.Success) {
        [System.Net.WebUtility]::HtmlDecode($match.Groups["value"].Value).Trim()
    }
}

function Get-AssetNames {
    param([string[]]$HtmlDocuments)

    $names = @{}
    foreach ($html in $HtmlDocuments) {
        foreach ($imageMatch in [regex]::Matches(
            $html,
            "<img\b[^>]*>",
            [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
        )) {
            $tag = $imageMatch.Value
            $source = Get-AttributeValue $tag "src"
            $name = Get-AttributeValue $tag "alt"
            $assetMatch = [regex]::Match($source, "/images/(?<asset>[^?`" ]+)")
            if (-not $assetMatch.Success -or [string]::IsNullOrWhiteSpace($name)) {
                continue
            }

            $asset = $assetMatch.Groups["asset"].Value
            if (-not $names.ContainsKey($asset)) {
                $names[$asset] = [System.Collections.Generic.HashSet[string]]::new(
                    [System.StringComparer]::Ordinal
                )
            }
            [void]$names[$asset].Add($name)
        }
    }
    $names
}

function Get-EntityNames {
    param(
        [string]$Html,
        [string]$LocalePath,
        [string]$Page
    )

    $names = @{}
    $hrefPrefix = "$LocalePath/$Page/"
    $pattern = '<a\s+href="' + [regex]::Escape($hrefPrefix) +
        '(?<slug>[a-z0-9][a-z0-9-]*)"[^>]*>(?<body>.*?)</a>'
    foreach ($linkMatch in [regex]::Matches(
        $Html,
        $pattern,
        [System.Text.RegularExpressions.RegexOptions]::Singleline
    )) {
        $nameMatch = [regex]::Match(
            $linkMatch.Groups["body"].Value,
            '<div\s+class="name(?:\s[^"]*)?"[^>]*>(?<name>.*?)</div>',
            [System.Text.RegularExpressions.RegexOptions]::Singleline
        )
        if (-not $nameMatch.Success) {
            continue
        }

        $name = [regex]::Replace($nameMatch.Groups["name"].Value, "<[^>]+>", "")
        $name = [System.Net.WebUtility]::HtmlDecode($name).Trim()
        if (-not [string]::IsNullOrWhiteSpace($name)) {
            $names[$linkMatch.Groups["slug"].Value] = $name
        }
    }
    $names
}

function Add-Term {
    param(
        [System.Collections.Generic.Dictionary[string, string]]$Terms,
        [string]$Source,
        [string]$Target,
        [string]$Origin
    )

    if (
        [string]::IsNullOrWhiteSpace($Source) -or
        [string]::IsNullOrWhiteSpace($Target) -or
        $Source -eq $Target
    ) {
        return
    }
    if ($Terms.ContainsKey($Source)) {
        if ($Terms[$Source] -ne $Target) {
            throw "Conflicting translation for '$Source': '$($Terms[$Source])' or '$Target' ($Origin)"
        }
        return
    }
    $Terms.Add($Source, $Target)
}

function ConvertTo-CsvField {
    param([string]$Value)

    if ($Value -match '[,"\r\n]') {
        return '"' + $Value.Replace('"', '""') + '"'
    }
    $Value
}

$documents = @{
    en = @{}
    zh = @{}
}
foreach ($page in $pages) {
    $documents.en[$page] = Get-PageHtml "" $page
    $documents.zh[$page] = Get-PageHtml "/zh-Hans" $page
}

$terms = [System.Collections.Generic.Dictionary[string, string]]::new(
    [System.StringComparer]::Ordinal
)

$englishAssets = Get-AssetNames @($pages | ForEach-Object { $documents.en[$_] })
$chineseAssets = Get-AssetNames @($pages | ForEach-Object { $documents.zh[$_] })
foreach ($asset in @($englishAssets.Keys | Sort-Object)) {
    if (
        -not $chineseAssets.ContainsKey($asset) -or
        $englishAssets[$asset].Count -ne 1 -or
        $chineseAssets[$asset].Count -ne 1
    ) {
        continue
    }
    Add-Term $terms @($englishAssets[$asset])[0] @($chineseAssets[$asset])[0] "asset $asset"
}

foreach ($page in $entityPages) {
    $englishEntities = Get-EntityNames $documents.en[$page] "" $page
    $chineseEntities = Get-EntityNames $documents.zh[$page] "/zh-Hans" $page
    foreach ($slug in @($englishEntities.Keys | Sort-Object)) {
        if ($chineseEntities.ContainsKey($slug)) {
            Add-Term $terms $englishEntities[$slug] $chineseEntities[$slug] "$page/$slug"
        }
    }
}

foreach ($entry in $curatedTerms.GetEnumerator()) {
    Add-Term $terms $entry.Key $entry.Value "curated core terminology"
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.Add("source,target,tgt_lng")
foreach ($source in @($terms.Keys | Sort-Object)) {
    $lines.Add(
        "$(ConvertTo-CsvField $source),$(ConvertTo-CsvField $terms[$source]),zh-CN"
    )
}

$outputDirectory = Split-Path $OutputPath -Parent
if (-not (Test-Path -LiteralPath $outputDirectory)) {
    New-Item -ItemType Directory -Path $outputDirectory | Out-Null
}
[System.IO.File]::WriteAllLines(
    $OutputPath,
    $lines,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "Wrote $($terms.Count) terms to $OutputPath"
