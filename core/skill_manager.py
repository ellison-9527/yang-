from pathlib import Path
import logging
import re
import yaml
# 存储所有扫描的skill，键为skill名称，值为skill对象
skills = {}

SKILLS_DIR =Path(__file__).parent.parent/"skills"
logger = logging.getLogger(__name__)

# 引用文件相关常量
MAX_REFERENCE_FILES = 30
EXCLUDE_PATTERNS = {"__pycache__", ".pyc", ".git", ".DS_Store", ".gitignore"}

TEXT_EXTENSIONS = {
    ".md", ".txt", ".py", ".json", ".yaml", ".yml", ".html", ".css",
    ".js", ".ts", ".toml", ".cfg", ".ini", ".sh", ".bat", ".xml",
    ".csv", ".rst", ".log",
}


"""引用资源文件"""


def get_skill_content_for_tool(name:str) -> str | None:
    """返回skill的正文内容和引用文件
         <skill_content name="{name}">
         skill.md中的content
         Base directory: skill技能包的绝对路径
         skill引用文件的相对路径
         <skill_files>
         。。。。
         </skill_files>
    """
    skill = skills.get(name)
    if not skill:
        return None
    parts = [f'<skill_content name="{name}">']
    parts.append(f"# Skill: {name}")
    parts.append("")
    parts.append(skill["system_prompt"])  # 正文内容

    references = skill.get("references", [])
    if references:
        parts.append("")
        parts.append(f"Base directory: {skill['dir']}")
        parts.append("")
        parts.append("<skill_files>")
        for ref in references:
            ext = Path(ref["abs_path"]).suffix.lower()
            file_type = "text" if ext in TEXT_EXTENSIONS else "binary"
            parts.append(f'<file path="{ref["path"]}" type="{file_type}" />')
        parts.append("</skill_files>")

    parts.append("</skill_content>")
    # print("get_skill_content_for_tool:\n","\n".join(parts))
    return "\n".join(parts)

def get_skill_reference_content(name: str, path: str) -> str | None:
        """按需读取指定 Skill 的单个引用文件内容"""
        skill = skills.get(name)
        if not skill:
            return None

        normalized_path = path.strip().replace("\\", "/") # 去除路径两端的空字符，并且将路径中的斜杠转换为正斜杠
        if not normalized_path:
            return None

        references = skill.get("references", [])
        matched_ref = next( # 使用生成器表达式遍历所有引用文件，找到路径匹配的那个
            (ref for ref in references if ref.get("path", "").replace("\\", "/") == normalized_path),
            None,
        )
        if not matched_ref:
            return None

        abs_path = Path(matched_ref["abs_path"]) # 获取绝对路径
        ext = abs_path.suffix.lower() # 提取文件扩展名并转为小写
        if ext not in TEXT_EXTENSIONS:
            return f'<file path="{matched_ref["path"]}">[二进制文件，未加载]</file>'

        try:
            content = abs_path.read_text(encoding="utf-8")
        except Exception:
            return f'<file path="{matched_ref["path"]}">[读取失败]</file>'

        return "\n".join([
            f'<file path="{matched_ref["path"]}">',
            content,
            "</file>",
        ])


def _scan_references(skill_dir: Path) -> list[dict[str, str]]:
    """扫描 Skill 目录下的引用资源文件（排除 SKILL.md），最多 MAX_REFERENCE_FILES 个"""
    references = []
    try:
        for ref_file in sorted(skill_dir.rglob("*")): # 遍历目录下的所有文件
            if not ref_file.is_file():
                continue
            if ref_file.name == "SKILL.md":
                continue
            if any(p in str(ref_file) for p in EXCLUDE_PATTERNS): # 忽略指定目录
                continue
            rel_path = ref_file.relative_to(skill_dir) # 相对路径
            references.append({
                "path": str(rel_path),
                "abs_path": str(ref_file),
            })
            if len(references) >= MAX_REFERENCE_FILES:
                break
    except Exception as e:
        logger.error(f"扫描引用文件失败 {skill_dir}: {e}")
    return references


def _parse_skill_md(file_path: Path) :
    """解析 SKILL.md 文件，返回 skill 配置字典（含引用文件列表）"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"读取 Skill 文件失败 {file_path}: {e}")
        return None

    # 解析 YAML frontmatter
    frontmatter = {}
    body = content
    # 解析带有 YAML front matter 格式的内容。捕获group(1) 元数据和group(2) 正文
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if match:
        try:
            frontmatter = yaml.safe_load(match.group(1)) or {}  # 将元数据转为字典
        except yaml.YAMLError as e:
            logger.error(f"解析 YAML frontmatter 失败 {file_path}: {e}")
            frontmatter = {}
        body = match.group(2)  # 正文

    # 目录名作为默认 name
    dir_name = file_path.parent.name
    name = frontmatter.get("name", dir_name)

    # 扫描引用文件
    references = _scan_references(file_path.parent)
    # print(name,frontmatter.get("enable"))
    # print(references)
    if frontmatter.get("enable")==False :
        return None
    return {
        "name": name,
        "description": frontmatter.get("description", ""),
        "system_prompt": body.strip(),  # 系统提示词为skill的正文内容
        "dir": str(file_path.parent),  # skill所在的目录的绝对路径
        "references": references,  # 相应的引用文件路径
    }


def _scan_directory(base_dir: Path):
    """扫描指定目录下的所有 Skill"""
    for skill_dir in sorted(base_dir.iterdir()): # 遍历目录下的所有子目录且按名称排序
        if not skill_dir.is_dir(): # 忽略非目录
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists(): # 忽略非 Skill 文件
            continue
        skill = _parse_skill_md(skill_file)
        # print(f"加载 Skill '{skill}'")
        if skill:
            # 本地 Skill 优先于远程同名 Skill
            if skill["name"] not in skills:
                skills[skill["name"]] = skill  # 将skill添加到skills字典中
            else:
                logger.debug(f"跳过远程 Skill '{skill['name']}'，本地已存在同名")

# 扫描所有的skill
def scan():
    skills.clear()   # 清空skill
    # 1. 扫描本地 skills 目录
    if not SKILLS_DIR.exists():
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    _scan_directory(SKILLS_DIR)


if __name__ == "__main__":
    scan()
    get_skill_content_for_tool("skill-creator")