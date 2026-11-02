"""Copy planning artifacts and constrain acceptance writes to those copies."""
import copy
import os
from pathlib import Path
from plan import digest, load_json, raw_hash, safe_target


def require(ok, message):
    if not ok:
        raise ValueError(message)


def target(raw, workspace):
    return safe_target(workspace / '_anchor.json', raw, workspace)


def relocate(value, old_anchor, new_anchor, workspace):
    """Preserve referents when a document moves; commands remain workspace-relative."""
    if isinstance(value, list):
        return [relocate(v, old_anchor, new_anchor, workspace) for v in value]
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    result = {k: relocate(v, old_anchor, new_anchor, workspace) for k, v in value.items()}
    if isinstance(value.get('path'), str):
        file = safe_target(old_anchor, value['path'], workspace)
        result['path'] = os.path.relpath(file, new_anchor.parent).replace(os.sep, '/')
    if isinstance(value.get('changedFiles'), list):
        result['changedFiles'] = [os.path.relpath(safe_target(old_anchor, p, workspace), new_anchor.parent).replace(os.sep, '/')
                                  if isinstance(p, str) else relocate(p, old_anchor, new_anchor, workspace)
                                  for p in value['changedFiles']]
    return result


def create(cases, plan, directory, workspace):
    workspace, directory = workspace.resolve(), directory.resolve()
    directory.relative_to(workspace)
    sources = [cases.resolve(), cases.with_suffix('.html').resolve(), plan.resolve(), plan.with_suffix('.md').resolve()]
    destinations = [directory / name for name in ('test-cases.json', 'test-cases.html', 'task-plan.json', 'task-plan.md')]
    require(len(set(sources)) == 4 and all(p.is_file() for p in sources), 'Planning JSON/HTML/Markdown sources must exist')
    require(not any(p.resolve() in sources for p in destinations), 'Acceptance copies must not overwrite planning sources')
    require(not any(p.exists() or p.is_symlink() for p in destinations), 'Acceptance copies already exist; resume instead of overwriting')
    for p in sources:
        p.relative_to(workspace)
    source = dict(artifactRoot=directory.relative_to(workspace).as_posix(),
                  testCasesPath=cases.resolve().relative_to(workspace).as_posix(),
                  taskPlanPath=plan.resolve().relative_to(workspace).as_posix(),
                  files=[dict(path=p.relative_to(workspace).as_posix(), sha256=raw_hash(p.read_bytes())) for p in sources])
    model = relocate(load_json(cases), cases, destinations[0], workspace)
    task_plan = relocate(load_json(plan), plan, destinations[2], workspace)
    task_plan['testCases']['path'] = 'test-cases.json'
    task_plan['testCases']['sha256'] = digest(model)
    payloads = [json_bytes(model), sources[1].read_bytes(), json_bytes(task_plan), sources[3].read_bytes()]
    directory.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for path, payload in zip(destinations, payloads):
            with path.open('xb') as stream:
                created.append(path)
                stream.write(payload)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return source, model, task_plan, destinations[0], destinations[2]


def json_bytes(value):
    import json
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def validate(record, workspace, outputs=(), check_sources=True):
    source = record.get('planningSource')
    require(isinstance(source, dict), 'Unisolated acceptance record: copy planning artifacts before any acceptance write')
    root = target(source['artifactRoot'], workspace)
    source_paths = {target(r['path'], workspace) for r in source['files']}
    expected_sources = {target(source['testCasesPath'], workspace), target(source['taskPlanPath'], workspace)}
    expected_sources |= {p.with_suffix('.html' if p.name == 'test-cases.json' else '.md') for p in expected_sources}
    require(source_paths == expected_sources and len(source['files']) == 4, 'Planning source manifest must cover all four originals')
    expected = {'testCasesPath': root / 'test-cases.json', 'taskPlanPath': root / 'task-plan.json'}
    for key, path in expected.items():
        require(target(record[key], workspace) == path.resolve() and path.resolve() not in source_paths,
                'Acceptance writes must target isolated planning copies')
    if 'contractsDirectory' in record:
        require(target(record['contractsDirectory'], workspace) == (root / 'contracts').resolve(), 'Contracts must stay in the acceptance artifact root')
    for output in outputs:
        output = Path(output).resolve()
        require(output not in source_paths and (root == output or root in output.parents), 'Acceptance output would modify a planning source or escape its artifact root')
    if check_sources:
        require(all(target(r['path'], workspace).is_file() and raw_hash(target(r['path'], workspace).read_bytes()) == r['sha256']
                    for r in source['files']), 'Planning source changed; review the new baseline before continuing acceptance')
    return source
