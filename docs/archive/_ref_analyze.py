import re, os, glob, json
from collections import defaultdict

base_dir = "D:/xinjian/project/prompt"

# Get all MD files (excluding .codeartsdoer)
md_files = []
for f in glob.glob(os.path.join(base_dir, '**/*.md'), recursive=True):
    rel = os.path.relpath(f, base_dir).replace('\\', '/')
    if '.codeartsdoer' not in rel:
        md_files.append(rel)
md_files.sort()

# Core docs (00-12)
core_pattern = re.compile(r'^\d\d_.*\.md$')
core_docs = [f for f in md_files if core_pattern.match(f)]

link_pattern = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

all_refs = []
file_anchors = {}

for filepath in md_files:
    full_path = os.path.join(base_dir, filepath)
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
    anchors = set()
    for h in headings:
        anchor = h.strip().lower()
        anchor = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', anchor)
        anchor = re.sub(r'[\s]+', '-', anchor)
        anchor = re.sub(r'-+', '-', anchor)
        anchor = anchor.strip('-')
        anchors.add(anchor)
    file_anchors[filepath] = anchors

    for match in link_pattern.finditer(content):
        text = match.group(1)
        target = match.group(2)

        if target.startswith('http://') or target.startswith('https://') or target.startswith('mailto:'):
            continue

        if '#' in target:
            parts = target.split('#', 1)
            target_path = parts[0]
            target_anchor = parts[1]
        else:
            target_path = target
            target_anchor = None

        if target_path:
            dir_of_src = os.path.dirname(filepath)
            resolved = os.path.normpath(os.path.join(dir_of_src, target_path))
            resolved = resolved.replace('\\', '/')
        else:
            resolved = filepath

        pos = match.start()
        preceding = [(m.start(), m.group(1).strip()) for m in re.finditer(r'^#+\s+(.+)$', content, re.MULTILINE) if m.start() < pos]
        source_section = preceding[-1][1] if preceding else '(文档头部)'

        if target_anchor:
            ref_type = '锚点引用'
        elif target_path:
            ref_type = '文档引用'
        else:
            ref_type = '未知'

        all_refs.append({
            'source_file': filepath,
            'source_section': source_section,
            'target_file': resolved,
            'target_anchor': target_anchor,
            'target_raw': target,
            'text': text,
            'ref_type': ref_type,
            'pos': pos
        })

# 4.1 Output
print("=" * 80)
print("4.1 全量Markdown链接与锚点引用扫描结果")
print("=" * 80)
print(f"\n共扫描 {len(md_files)} 个MD文件，发现 {len(all_refs)} 个内部引用\n")

refs_by_source = defaultdict(list)
for r in all_refs:
    refs_by_source[r['source_file']].append(r)

for src in sorted(refs_by_source.keys()):
    refs = refs_by_source[src]
    print(f"\n{src} ({len(refs)} 个引用)")
    for r in refs:
        anchor_str = f"#{r['target_anchor']}" if r['target_anchor'] else ''
        print(f"  -> [{r['text']}]({r['target_raw']}) | {r['ref_type']} | 章节: {r['source_section'][:40]}")

# 4.2 Validate
print("\n" + "=" * 80)
print("4.2 引用完整性校验")
print("=" * 80)

broken_links = []
invalid_anchors = []
valid_refs = []
existing_files = set(md_files)

for r in all_refs:
    target_exists = r['target_file'] in existing_files
    if not target_exists and r['target_file']:
        broken_links.append(r)
        continue
    if r['target_anchor'] and r['target_file'] in file_anchors:
        available = file_anchors[r['target_file']]
        norm = r['target_anchor'].lower()
        norm = re.sub(r'[^\w\s\u4e00-\u9fff-]', '', norm)
        norm = re.sub(r'[\s]+', '-', norm)
        norm = re.sub(r'-+', '-', norm)
        norm = norm.strip('-')
        if norm not in available and r['target_anchor'] not in available:
            invalid_anchors.append(r)
            continue
    valid_refs.append(r)

print(f"\n断链（目标文件不存在）: {len(broken_links)} 个")
for r in broken_links:
    print(f"  X [{r['text']}]({r['target_raw']}) in {r['source_file']} -> {r['target_file']}")

print(f"\n失效锚点: {len(invalid_anchors)} 个")
for r in invalid_anchors:
    print(f"  ! [{r['text']}]({r['target_raw']}) in {r['source_file']} -> #{r['target_anchor']} not in {r['target_file']}")

print(f"\n有效引用: {len(valid_refs)} 个")

# 4.5 Cycles
print("\n" + "=" * 80)
print("4.5 全局引用关系与循环引用检测")
print("=" * 80)

adj = defaultdict(set)
for r in valid_refs:
    if r['source_file'] in core_docs and r['target_file'] in core_docs:
        if r['source_file'] != r['target_file']:
            adj[r['source_file']].add(r['target_file'])

cycles = []
visited_global = set()

def find_cycles_dfs():
    visited = set()
    rec_stack = set()
    path = []
    found_cycles = []

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        for neighbor in sorted(adj[node]):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                idx = path.index(neighbor)
                cycle = path[idx:] + [neighbor]
                found_cycles.append(cycle[:])
        path.pop()
        rec_stack.remove(node)

    for node in core_docs:
        if node not in visited:
            dfs(node)
    return found_cycles

cycles = find_cycles_dfs()
if cycles:
    print(f"\n检测到 {len(cycles)} 个循环引用:")
    for i, c in enumerate(cycles):
        print(f"  循环 {i+1}: {' -> '.join(c)}")
else:
    print("\n未检测到循环引用")

print("\n核心文档引用关系图:")
for src in core_docs:
    targets = adj.get(src, set())
    if targets:
        print(f"  {src} -> {', '.join(sorted(targets))}")
    else:
        print(f"  {src} -> (无出引用)")

# 4.7 Path conventions
print("\n" + "=" * 80)
print("4.7 引用路径规范校验")
print("=" * 80)

absolute_path_refs = []
for r in all_refs:
    raw = r['target_raw']
    if raw.startswith('/') or (len(raw) >= 2 and raw[1] == ':'):
        absolute_path_refs.append(r)

if absolute_path_refs:
    print(f"\n发现 {len(absolute_path_refs)} 个绝对路径引用:")
    for r in absolute_path_refs:
        print(f"  X [{r['text']}]({r['target_raw']}) in {r['source_file']}")
else:
    print("\n所有引用均使用相对路径 ✅")

# Stats
print("\n" + "=" * 80)
print("引用统计汇总")
print("=" * 80)

out_counts = defaultdict(int)
for r in all_refs:
    out_counts[r['source_file']] += 1
print("\n出引用统计:")
for f in sorted(out_counts.keys(), key=lambda x: -out_counts[x]):
    print(f"  {f}: {out_counts[f]}")

in_counts = defaultdict(int)
for r in all_refs:
    if r['target_file'] in core_docs or r['target_file'] in md_files:
        in_counts[r['target_file']] += 1
print("\n入引用统计:")
for f in sorted(in_counts.keys(), key=lambda x: -in_counts[x]):
    print(f"  {f}: {in_counts[f]}")

# Save structured data for later use
with open(os.path.join(base_dir, '_ref_data.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'all_refs': all_refs,
        'broken_links': broken_links,
        'invalid_anchors': invalid_anchors,
        'valid_refs': valid_refs,
        'cycles': cycles,
        'core_docs': core_docs,
        'adj': {k: list(v) for k, v in adj.items()},
        'in_counts': dict(in_counts),
        'out_counts': dict(out_counts)
    }, f, ensure_ascii=False, indent=2)

print("\n分析数据已保存至 _ref_data.json")
