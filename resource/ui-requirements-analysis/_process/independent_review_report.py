"""由独立评审上下文保存已完成的人工语义判断；不运行完整业务双图门禁。"""
import hashlib
import json
from pathlib import Path

root = Path(__file__).parent.parent
load = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
m = load(root/'analysis.json')
manifest = load(root/'manifest.json')
verification = load(root/'_process/reviewer-verification.json')
browser = load(root/'_process/evidence/browser-observation.json')
assert m['semanticDigest'] == verification['semantic_actual'] == browser['semanticDigest'] == '3570a415f249369d48c98e830e2f5a4ae0a3d800a846dd7b1291a21ecd04943d'
assert manifest['bundleDigest'] == verification['bundle_actual'] == browser['bundleDigest'] == '2b415cb32b56016e22148e65cd6ec8af6a689877314695e81b3d018989d2bf53'
assert browser['htmlSha256'] == sha(root/'review.html')

# 逐张实际查看PNG后写下的独立判断，不由场景数量或作者的passed推导。
observations = [
('V01','中部引导面板、斜向反光、记事图标、创建按钮和下部留白均与空态目标对应，区别于图02的卡片内容。'),
('V02','两张不同方向卡片、周进度、截止提示、已记录卡片均可见；同屏局部目标没有提升为新整页，长画板高度保留。'),
('V03','运行中选中且另两筛选未选，四卡与计划导航构成独立整页；没有把未选项推导为新的筛选结果画板。'),
('V04','方向/类型为浅色选中，星期七项为深石墨；这两种已有选中材质有区分，未枚举星期组合。'),
('V05','目标数量面板替代星期行，部分周说明单独存在；数字可变并未抹去该面板的结构与选中样式。'),
('V06','一次性选项、方向说明卡、截止字段与保存任务按钮确实构成不同表单目标，未补业务日期验证。'),
('V07','问题卡、成功浅绿选中、另外两项未选、已填备注与上下两条提示有承载；没有补失败/跳过选中整页。'),
('V08','问题文案、不要做说明、做到了/发生了文案与已选择说明行和图07不同，分开对照有独立视觉义务。'),
('V09','上方原成功标签与下方失败浅红选中同时存在，分析准确分开两个区域，未当成互相冲突的保存结果。'),
('V10','历史日期面板与三行时间/不可修改提示确实可见；日期值为参数，未据日期生成多状态。'),
('V11','今日9日无下标且浅底加粗，8日独立边框及2/5，5日绿色勾，6/7日0/1，跨月弱色；五明细含四类结果，均有承载。'),
('V12','百分比金属面板、两列统计、成功/跳过/未记录和已修改/可补记文字均保留，未推导分母算法。'),
('V13','周进度面板和独立周统计卡有别于图12；最近记录最后一项确为“空白”，分析未替换为“未记录”。'),
('V14','逾期标签、截止面板、现在完成与并列红/中性次按钮、时间线均对应；没有把其他同名任务画板串为时间线。'),
('V15','每天选中、指定星期未选、结束字段、生效面板和面板外说明均有承载；未补指定星期展开页。'),
('V16','实际为暂停确认卡、单段恢复辅助说明、待生效申请卡三个局部样例；没有恢复按钮或完整恢复页面，不应补画。'),
('V17','线性归档图标、金属主按钮、中性次按钮及卡外说明有承载；和图18红色危险强调确实不同。'),
('V18','现图没有独立危险图标；红标题、两级说明、红边红字删除按钮和中性取消构成目标，未从PRD概括词补图。'),
('V19','手机图标与金属介绍面板、数据/时区分组、版本卡结构有承载；说明只作为可见文案而非功能要求。'),
('V20','浅色中性面板、红图标、深色标题、无勾主色“已选成功”和保留内容框与分析相符；未误用图23黄色面板。'),
('V21','任务摘要、实际完成日期、日期解释、备注、提交时间说明与保存完成记录构成独立表单目标，没有日期弹层稿。'),
('V22','绿色大字结果、日期/时区/提交时间、备注卡与只读说明卡和返回按钮均有承载；没有修改表单。'),
('V23','浅黄警示面板、警示色边框/图标、绿色带勾已选成功、尚未保存标题和两按钮均区别于图20。'),
]

rubric = [
    {
      'criterion_id':'source_consistency','applicability':'limited_to_accessible_exported_sources','conclusion':'passed',
      'scope':'PRD第1–6节、23张导出图、允许使用的映射字段、设计令牌及设计树快照；不包含原稿实时一致性。',
      'evidence':[
        '_process/evidence/source-coverage.md：102项原文处置逐项核对；第3节23画板均映射。',
        'analysis.json.scope/requirement：唯一UI-001，布局/组件/状态/视觉参数是细化，未导入历史FR/AT或实现状态。',
        '_process/reviewer-verification.json：27份缓存SHA256及与当前源文件逐字节一致；此结论不覆盖resource/ui.pen。'
      ]
    },
    {
      'criterion_id':'branch_meaning','applicability':'visual_state_admission_only','conclusion':'passed',
      'scope':'按state-boundary.md检查页面级视觉场景的四项准入、局部目标和参数；业务分支与自环不适用。',
      'evidence':[
        'analysis.json.scenarios V01–V23：每项均有PRD/PNG/TREE来源、当前condition/facts、相邻场景distinction及regions目标；下附23项独立PNG观察。',
        '_process/evidence/source-coverage.md §3；V04方向/类型与星期选中材质不同，V08增加已选择说明，V09原记录/当前选中分区，均有具体差异。',
        'V16-R1/R2/R3局部承载暂停卡、恢复说明、待生效卡，没有拼出完整恢复页；V11日期格只保留已画组合。',
        '当前业务迁移集合为空，自环集合为空（[]）；未创建进入/展示/查看等假事件。'
      ],
      'self_loops_reviewed':[]
    },
    {
      'criterion_id':'atomicity','applicability':'not_applicable_to_behavioral_transition_atomicity','conclusion':'not_applicable',
      'scope':'当前PRD只有静态视觉UI-001，不存在一迁移一行为的业务模型。',
      'evidence':['PRD §1、§1.2、§6；analysis.json.requirement.countingRule：23场景、50区域和公共约束不计作新增功能需求。'],
      'visual_counting_check':'已核对唯一UI-001，未按按钮、样式或画板拆功能需求；该检查不等于业务原子性通过。'
    },
    {
      'criterion_id':'guards_and_complements','applicability':'not_applicable_to_business_guards_paths_and_witnesses','conclusion':'not_applicable',
      'scope':'没有有来源的入口、守卫、迁移或业务可执行路线，不能要求或补造。',
      'evidence':[
        'PRD §1.2、§5：存储/统计/路由闭环/跨日逻辑不作为完成条件；analysis.json.applicability.fullTransitionPipeline=false。',
        'V05数量值、V10历史日期、V14逾期信息、V16生效文字、V20/V23保留输入均限制为可见场景，未补合法域、重试效果或互斥链路。'
      ]
    },
    {
      'criterion_id':'ui_mapping','applicability':'static_visual_targets','conclusion':'passed',
      'scope':'当前导出资料的23画板、50区域、共同约束和局部节点映射；不判断产品截图与设计相似程度。',
      'evidence':[
        '_process/evidence/source-coverage.md §3；全部23张PNG已由此独立上下文逐张实际查看，见frame_reviews。',
        '_process/reviewer-verification.json：全部50区域nodeRefs按节点ID+完整路径+名称/文案核对，无错误；23内嵌PNG逐字节一致。',
        'C01区分393逻辑宽度、2×导出和长画板；C03保留25/36/32/19/23/11sp局部值；C05不把渐变/高光/阴影平面化。',
        'V13空白、V18无独立危险图标、V20主色无勾、V23绿色带勾及浅黄面板均按实际图保留，没有由公共参数覆盖局部差异。',
        'C08允许名称/日期/数量/备注变化，同时明确固定视觉文案和结构仍分别核对；进度比例、选中样式与警示表达仍在区域检查点中。'
      ]
    },
    {
      'criterion_id':'unresolved_decisions','applicability':'accessible_visual_analysis','conclusion':'passed',
      'scope':'已缓存资料内未发现需新增业务答案或设计选择的冲突；原稿实时核对仍受限。',
      'evidence':[
        'analysis.json.questions=[]与PRD明确排除稿外场景/设备矩阵/阈值一致，不把缺稿自动变为待设计任务。',
        'L1明确resource/ui.pen当前内容未实时核对；L2明确未读取实现、未采集产品截图、未进行应用验收。',
        'decisions解释图16局部层级和图18没有独立图标；没有使用历史规则解决视觉判断。'
      ]
    },
    {
      'criterion_id':'convergence','applicability':'bounded_exported_source_coverage','conclusion':'passed',
      'scope':'仅对当前可访问PRD和导出资料的来源到模型/模型到来源覆盖作结论；完整双图可达性及发布门禁不适用。',
      'evidence':[
        '_process/evidence/source-coverage.md逐条处置；本独立上下文全量复核23场景/50区域，未发现当前已画主要样例遗漏或无依据新增。',
        'analysis.json.rounds作者复核在当前摘要有23项；authorAuditComplete只作为作者声明，未替代本独立检查。',
        '生成器已明确digestExclusions只排除convergence/phase/review/rounds/semanticDigest，排除规则本身参与哈希；独立复算与当前声明一致。'
      ]
    },
    {
      'criterion_id':'html_observation','applicability':'adapted_static_read_only_review','conclusion':'passed',
      'scope':'对静态视觉只读审查页核对导航、图像、目标/来源/参数/限制可读性；完整Canvas双图及业务链路交互不适用。',
      'evidence':[
        '已读取review.html的嵌入数据和与review-template.html一致的可执行页壳；模型内容及内嵌23图与当前包一致。',
        '_process/evidence/browser-observation.json明确主代理真实CUA浏览上下文、URL、当前semanticDigest/bundleDigest及HTML SHA256，已逐项独立核对与最终文件一致。',
        '该实测记录逐一列出23画板imageReady=true、horizontalOverflow=false与共50区域；四视图、恢复搜索、图16来源展开、图23参数展开有实际DOM文本，errorLogs为空。',
        '独立查看更新后的review-desktop、review-frame16、review-source-coverage、review-scope、review-parameters共5张浏览截图；图16局部目标和展开来源可读，参数显示为中文标签/实际色值，验收映射已使用区域/约束名称。'
      ],
      'observation_provenance':'浏览器由主代理实际操作；此独立上下文未重入浏览器，而是核对绑定最终HTML的实测记录、DOM文本和截图。该结论仅覆盖静态只读审查页，不覆盖原rubric的Canvas双图/最短链路交互。'
    }
]

findings = [
  {'id':'IR-001','priority':'P2','status':'resolved','title':'语义摘要在最终模型元数据变更前计算，绑定当前内容失效',
   'evidence_ref':'_process/build_review.py；_process/reviewer-verification.json',
   'expected':'明确且稳定的摘要排除键规则下，最终analysis.json重算值应与声明semanticDigest一致。',
   'actual':'初次复算声明562a00c3ad5b9875d68f519013d714dc97eaab0b076fdf0daeceb90bf0052e06，按生成器相同规则实际a53955fd76337e1281cb6d4d694d5592d4630a0230e2f1ed4f33588a7aa4cd29；manifest文件与bundle哈希自身一致。',
   'repair':'生成器显式排除派生审查元数据，规则本身参与语义哈希；主代理连续两次重建后，本上下文按相同规则独立重算与3570a415f249369d48c98e830e2f5a4ae0a3d800a846dd7b1291a21ecd04943d一致。'},
  {'id':'IR-002','priority':'P3','status':'resolved','title':'局部设计参数在审查页显示原始字段和值',
   'evidence_ref':'review.html/styleText；_process/review-template.html',
   'expected':'设计参数以可理解的标签和值呈现，避免直接展现内部字段结构。',
   'actual':'初读HTML样式函数直接生成fontSize、fontWeight、fill、$text与fill_container等；尚未以浏览器运行独立确认。',
   'repair':'已静态核对styleText改为中文标签、色值与“随容器铺满”等值；在最终HTML绑定的browser-observation.json.renderedParameters及review-parameters.png实际展开内容复核满足。'},
  {'id':'IR-003','priority':'P3','status':'resolved','title':'来源覆盖的目标描述仍残留内部字段和约束编号',
   'evidence_ref':'_process/evidence/review-source-coverage.png；review.html/renderCoverage',
   'expected':'画板/区域/公共约束以名称表达目标，可保留PRD原有UI-001与A01编号。',
   'actual':'实际截图含“全部23画板及各自regions”“各场景regions；C01、C04”“C02–C05”。',
   'repair':'已在HTML/Markdown显示层映射为区域检查点、界面事实与完整约束名称；最终browser-observation.json.coverage.acceptanceTable和更新后的review-source-coverage.png实际内容复核满足，主模型含义未改。'}
]

evidence_paths = ['analysis.json','analysis.md','review.html','manifest.json','_process/design-index.json','_process/evidence/source-coverage.md','_process/reviewer-verification.json']
evidence_paths += [s['evidencePath'] for s in m['sources']]
evidence_paths += ['_process/evidence/browser-observation.json','_process/evidence/browser-frame-checks.json']
evidence_paths += ['_process/evidence/'+name+'.png' for name in ['review-desktop','review-frame16','review-source-coverage','review-scope','review-parameters']]
report = {
  'report_kind':'independent_static_visual_requirements_review',
  'status':'completed_with_documented_limitations',
  'context_ref':'/root/visual_analysis_review',
  'independent_context':True,
  'review_scope':'UI-001静态视觉分析草案；只对当前可访问PRD与导出资料及静态审查页作限定结论。',
  'summary':'23个画板级目标、50个区域检查点、共同约束及来源覆盖在当前导出资料范围内有据且未发现开放语义问题；3项发现已修复并独立复核。原稿实时一致性、产品视觉验收和用户最终确认仍未完成，完整业务双图门禁不适用且未运行。',
  'review_basis':['.codex/skills/requirements-analysis/SKILL.md','.codex/skills/requirements-analysis/references/state-boundary.md','.codex/skills/requirements-analysis/references/gate-rules.md'],
  'semantic_digest':m['semanticDigest'],
  'bundle_digest':manifest['bundleDigest'],
  'digest_verification':verification,
  'reviewed_ids':['UI-001']+[s['id'] for s in m['scenarios']]+[r['id'] for s in m['scenarios'] for r in s['regions']]+[c['id'] for c in m['sharedConstraints']]+[a['id'] for a in m['acceptance']]+[s['id'] for s in m['sources']]+[c['id'] for c in m['coverage']]+['L1','L2'],
  'frame_reviews':[{'scenario_id':identity,'source_ref':next(s['imagePath'] for s in m['scenarios'] if s['id']==identity),'conclusion':'supported_visual_target','observation':observation} for identity,observation in observations],
  'rubric':rubric,
  'findings':findings,
  'open_findings':[],
  'fixed_skill_pipeline':{'applicability':'not_applicable_to_static_visual_scope','run':False,'passed':False,'published':False,'explanation':'本报告含两个行为rubric不适用项及限定适用的HTML观察，不构成固定完整门禁八项全部通过，不用于assert/publish。'},
  'evidence_files':[{'path':p,'sha256':sha(root/p)} for p in dict.fromkeys(evidence_paths)],
  'limitations':[
    '原稿resource/ui.pen当前内容未实时访问，本复核只确认当前已缓存/可读取导出资料；未把该缺口写为通过。',
    '未读取应用实现、未运行应用或采集产品截图，未进行UI-001的产品视觉验收。',
    '当前为静态视觉分析草案，完整业务迁移双图与其固定assert/publish门禁不适用且未运行；本报告不是该流程的通过证明。',
    '本上下文未操作浏览器；HTML观察基于主代理实际CUA运行后提供的记录、DOM文本和5张截图，并独立核验其绑定当前最终HTML哈希。未声称本独立上下文直接执行过浏览交互。',
    '没有获得用户最终确认；本报告不构成人工验收或发布。'
  ]
}
(root/'_process/model-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'reviewed_id_count':len(report['reviewed_ids']),'semantic_digest':report['semantic_digest'],'bundle_digest':report['bundle_digest']},ensure_ascii=False))
