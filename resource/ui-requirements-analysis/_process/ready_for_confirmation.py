from pathlib import Path
import sys,json
w=Path(__file__).resolve().parent
sys.path.insert(0,str(w.parent.parent.parent/'.codex/skills/requirements-analysis/scripts'))
import workflow as wf
m,state=wf.load_current(w.parent)
report=wf.read(w/'model-review.json')
errors,pending=wf.check_review(report,m,wf.read(w.parent/'manifest.json'),wf.contract(w.parent),w.parent)
if errors or pending:raise ValueError(str({'errors':errors,'pending':pending}))
state.update(waiting_for_user=True,pause_reason='awaiting_final_confirmation',
    next_action='全部非最终确认门禁通过后展示当前HTML与分析结论，请用户整体确认；仅在收到真实回复后写acceptance.json，再assert/publish。')
wf.write(w/'run-state.json',state)
wf.save_current(w.parent)
print('Current working state saved; independent report verified. Run the standard assert command.')

