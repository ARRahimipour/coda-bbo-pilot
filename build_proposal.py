"""Build the English CODA-BBO research proposal from the recorded pilot outputs.

The proposal narrative is kept here so the document can be regenerated without
external services. Experiment tables and figures come from results/ and figures/;
this script does not execute or reinterpret the optimization benchmark.
"""

import json
import re
from pathlib import Path

import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
# Reuse the supplied layout so regenerated documents stay comparable.
BASE = Path(__file__).resolve().parent
R = BASE / 'results'
doc = Document()
sec = doc.sections[0]
sec.top_margin = Inches(0.72)
sec.bottom_margin = Inches(0.65)
sec.left_margin = sec.right_margin = Inches(0.78)
sec.page_width = Inches(8.5)
sec.page_height = Inches(11)
styles = doc.styles
for name in ['Normal', 'Body Text']:
    styles[name].font.name = 'Calibri'
    styles[name].font.size = Pt(11)
    styles[name].paragraph_format.space_after = Pt(7)
    styles[name].paragraph_format.line_spacing = 1.12
for name, size in [('Title', 30), ('Subtitle', 15), ('Heading 1', 19), ('Heading 2', 13)]:
    styles[name].font.name = 'Calibri'
    styles[name].font.size = Pt(size)
    styles[name].font.color.rgb = RGBColor(0, 0, 0)
    styles[name].paragraph_format.space_after = Pt(10)
footer = sec.footer.paragraphs[0]
footer.alignment = 2
r = footer.add_run('CODA BBO research proposal  |  ')
r.font.size = Pt(9)
fld = OxmlElement('w:fldSimple')
fld.set(qn('w:instr'), 'PAGE')
footer._p.append(fld)

def p(s, style=None):
    """Add one paragraph to the proposal, optionally with a Word style."""
    return doc.add_paragraph(s, style)

def h(s):
    """Add a subsection heading."""
    doc.add_heading(s, 2)

def page(title):
    """Start a new numbered proposal section."""
    doc.add_page_break()
    doc.add_heading(title, 1)

def table(headers, rows, widths=None):
    """Insert a bordered table with repeating headers and non-splitting rows."""
    t = doc.add_table(rows=1, cols=len(headers))
    t.autofit = False
    if widths:
        for c, w in zip(t.columns, widths):
            c.width = Inches(w)
    for c, txt in zip(t.rows[0].cells, headers):
        c.text = str(txt)
    for row in rows:
        for c, txt in zip(t.add_row().cells, row):
            c.text = str(txt)
    for i, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement('w:cantSplit')
        trPr.append(cant)
        if i == 0:
            rep = OxmlElement('w:tblHeader')
            trPr.append(rep)
        for j, c in enumerate(row.cells):
            if widths:
                c.width = Inches(widths[j])
            tcPr = c._tc.get_or_add_tcPr()
            b = OxmlElement('w:tcBorders')
            for e in ['top', 'left', 'bottom', 'right']:
                x = OxmlElement('w:' + e)
                x.set(qn('w:val'), 'single')
                x.set(qn('w:sz'), '4')
                x.set(qn('w:color'), 'D9D9D9')
                b.append(x)
            tcPr.append(b)
            mar = OxmlElement('w:tcMar')
            for side in ['top', 'left', 'bottom', 'right']:
                x = OxmlElement('w:' + side)
                x.set(qn('w:w'), '85')
                x.set(qn('w:type'), 'dxa')
                mar.append(x)
            tcPr.append(mar)
            if i == 0:
                fill = OxmlElement('w:shd')
                fill.set(qn('w:fill'), 'E8EFF5')
                tcPr.append(fill)
            for par in c.paragraphs:
                par.paragraph_format.space_after = Pt(2)
                par.paragraph_format.line_spacing = 1.03
                for run in par.runs:
                    run.font.size = Pt(9)
                    run.bold = i == 0
    p('')
    return t

def fig(name, caption, width=6.8):
    """Insert a figure produced by the analysis script and its caption."""
    doc.add_picture(str(BASE / 'figures' / name), width=Inches(width))
    p(caption, 'Caption')
# Load measured results; the text below must not claim any unexecuted study.
summary = pd.read_csv(R / 'summary.csv')
comp = pd.read_csv(R / 'comparisons.csv')
fam = pd.read_csv(R / 'family_auc.csv')
final = pd.read_csv(R / 'final_errors.csv')
runs = pd.read_csv(R / 'runs.csv')
manifest = json.loads((R / 'manifest.json').read_text())
ood = json.loads((R / 'ood.json').read_text())
sources = json.loads((R / 'sources.json').read_text())
vsde = comp[comp.baseline == 'DE'].iloc[0]
vsadapt = comp[comp.baseline == 'Adaptive-DE'].iloc[0]
vsno = comp[comp.baseline == 'No-OOD'].iloc[0]
p('CODA BBO', 'Title')
p('Continual OOD Aware Dynamic Algorithm Design', 'Subtitle')
p('A doctoral research proposal for self generating and online reconfigurable black box optimizers', 'Subtitle')
p('English research proposal with an executed computational pilot')
p('Prepared for doctoral supervision and research planning\n16 October 2026')
h('Purpose and main conclusion')
p(
    'We propose an optimizer designer that can recognize when prior experience is '
    'unreliable, decide whether changing an optimizer is worth its cost, and retain '
    'useful design experience across tasks. The scientific question is whether these '
    'decisions improve performance on unfamiliar problems under a strict evaluation '
    'budget.'
)
p(
    f"This proposal includes an executed stage zero pilot: {manifest['runs']:,} "
    f"optimization runs, {manifest['objective_evaluations']:,} budgeted objective "
    "evaluations, six analytic function families, six methods, and 12 passing "
    "software tests. It supplies reproducible code, raw run records, figures, "
    "and a DOI verification record. The pilot implements bounded operator "
    "compositions and heuristic online decisions. It does not implement the "
    "proposed learned generator, calibrated transfer risk, or continual memory."
)
p(
    "Across this small benchmark, CODA-pilot changes mean normalized log-error "
    f"AUC relative to DE by {vsde.relative_auc_reduction_pct:.2f}% in the "
    "improvement direction. The exploratory family-bootstrap interval is "
    f"[{vsde.ci_low:.2f}, {vsde.ci_high:.2f}]%. These observations motivate "
    "the next experiments; they do not establish state-of-the-art performance "
    "or validate the complete thesis."
)
h('Reading guide')
p(
    'The first part develops the research problem and proposed method. The middle part '
    'reports the implemented pilot and its measured results. The final part specifies '
    'the larger validation study, milestones, risks, reproducibility instructions, and '
    'original journal references from 2022 through 2026.'
)
page('1 Abstract and research objectives')
p(
    'Black-box optimization is often conducted with a limited number of expensive '
    'objective evaluations. The best search behavior can depend on the problem '
    'landscape, the remaining budget, and changes in the environment. Algorithm '
    'selection and parameter adaptation address parts of this difficulty, while '
    'automated algorithm design can construct more flexible search procedures. A '
    'remaining research challenge is deciding when prior design knowledge should be '
    'trusted and when the optimizer itself should be revised.'
)
p(
    'CODA-BBO will combine a representation of the observed search trajectory with a '
    'representation of the executable optimizer. A transfer-risk model will estimate '
    'the consequences of retaining or modifying that optimizer. A controller will '
    'choose among keeping the current design, tuning parameters, editing its structure, '
    'or generating a new bounded program. Candidate programs will be validated and '
    'compared through budgeted trials. A memory will retain successful designs and '
    'failed transfers, with explicit controls for forgetting and negative transfer.'
)
p(
    'The first research scope is bounded, continuous, single-objective minimization. '
    'Distribution shift across tasks will be studied separately from within-task '
    'objective drift. Frozen evaluation will measure generalization without test-time '
    'learning. Continual evaluation will use ordered task streams and report both '
    'adaptation and retention. This separation is necessary because an optimizer that '
    'improves through exposure to test tasks is not demonstrating the same capability '
    'as a frozen optimizer facing a new task.'
)
p(
    'The immediate contribution of the included code is narrower: it demonstrates '
    'evaluation accounting, bounded program execution, candidate trials, ablations, and '
    'a reproducible analysis workflow. The pilot uses a small handcrafted grammar and a '
    'frozen novelty statistic. Its findings are treated as feasibility evidence and as '
    'a diagnostic of where a learned controller could matter.'
)
h('Objectives')
table(
    ['Objective', 'Observable evidence'],
    [
        ('O1  Transfer awareness', 'Risk scores predict harmful reuse beyond geometric novelty alone.'),
        (
            'O2  Budgeted reconfiguration',
            'Online edits improve anytime quality after all trial costs are charged.',
        ),
        (
            'O3  Valid executable generation',
            'Generated programs satisfy type, resource, and state compatibility constraints.',
        ),
        (
            'O4  Continual design',
            'Experience improves later tasks without unacceptable forgetting or negative transfer.',
        ),
        (
            'O5  Reproducible evaluation',
            'Whole-family holdouts, complete budgets, raw records, and paired comparisons.',
        ),
    ],
    [1.65, 5.2],
)
page('2 Problem statement and scope')
p(
    'Let a task provide an objective f over a bounded domain X contained in R^d. The '
    'optimizer may query points and observe scalar values but does not receive '
    'gradients, the analytic expression, the identity of the function family, or the '
    'optimum. The initial study minimizes deterministic objectives. Noise, changing '
    'objectives, and mixed variables are extensions that require separate protocols.'
)
p(
    'The optimization state contains a population or archive, observed objective '
    'values, the incumbent, remaining evaluation budget, and execution statistics. The '
    'algorithm is itself an object A represented in a restricted language. A design '
    'controller observes the permitted state and selects an action a from keep, tune, '
    'edit, or generate. The central cost is not only the number of calls made by the '
    'final chosen optimizer: probes, rejected candidate trials, and reassessments also '
    'consume the same task budget.'
)
h('Three different changes')
table(
    ['Phenomenon', 'Meaning', 'Required measurement'],
    [
        (
            'Task distribution shift',
            'A new task differs from the meta-training distribution.',
            'Family holdout and predictive transfer risk.',
        ),
        (
            'Objective drift',
            'The objective changes during one optimization run.',
            'Change detection delay and tracking error.',
        ),
        (
            'Policy induced change',
            'Search statistics change because the optimizer changed its sampling.',
            'Action-conditioned calibration and fixed diagnostic probes.',
        ),
    ],
    [1.45, 2.6, 2.8],
)
p(
    'An unusual trajectory is not by itself evidence that the environment changed. A '
    'successful local search can shrink population diversity and alter observed fitness '
    'statistics. CODA-BBO will therefore condition the risk model on the current '
    'program and recent actions. Fixed-location reevaluations will be used for drift '
    'tests, and their objective costs will be counted.'
)
h('Initial boundaries')
p(
    'The primary dimensions will be 5, 10, and 20. Single-objective, box-constrained '
    'problems provide a tractable first setting for formal program interfaces and '
    'controlled comparisons. Multi-objective optimization, unconstrained code '
    'synthesis, and deployment on physical systems are outside the first validation '
    'stage. Multi-objective journal papers are used for methodological context, not as '
    'direct evidence about the proposed single-objective task.'
)
p(
    'Success will mean a demonstrated advantage on specified held-out distributions '
    'with controlled costs. We do not seek a universally superior optimizer. The value '
    'of the framework depends on identifying where adaptation is useful and where '
    'retaining a strong fixed method is the better decision.'
)
page('3 Research questions and hypotheses')
table(
    ['Question', 'Hypothesis', 'Falsification condition'],
    [
        (
            'RQ1  What signals predict harmful transfer?',
            (
                'Program-conditioned trajectory features improve transfer-loss prediction over '
                'landscape features alone.'
            ),
            'No improvement in held-out calibration or risk ranking.',
        ),
        (
            'RQ2  When should structure change?',
            'A cost-aware controller improves AUC over parameter tuning at equal total budget.',
            'Gains disappear after rejected trials and inference cost are charged.',
        ),
        (
            'RQ3  Does bounded generation help?',
            (
                'Validated structural edits outperform a matched fixed portfolio on difficult '
                'held-out tasks.'
            ),
            'A portfolio with equal training and trial budget matches the result.',
        ),
        (
            'RQ4  Does memory help over time?',
            'A success-and-failure memory improves forward transfer with controlled forgetting.',
            'Benefits depend on task identity leakage or favorable ordering.',
        ),
        (
            'RQ5  Is drift handling distinct?',
            'Action-conditioned monitoring reduces false alarms compared with unconditioned novelty.',
            'It confuses policy changes with objective changes at the same false-alarm budget.',
        ),
    ],
    [1.55, 2.6, 2.7],
)
p(
    'The pilot directly exercises part of RQ2 and the engineering prerequisites of RQ3. '
    'It offers only a weak diagnostic for RQ1 because the novelty score is not trained '
    'to predict transfer loss. RQ4 and RQ5 require additional implementations and are '
    'not answered by the static results in this proposal.'
)
h('Decision criteria for the full study')
p(
    'The primary endpoint will be an anytime performance measure on predefined held-out '
    'tasks. A useful result must improve the primary endpoint against strong matched '
    'baselines and report uncertainty at the task-family level. A practical target is a '
    '5% relative AUC reduction without more than a 5% deterioration on reference tasks. '
    'These thresholds are proposed engineering criteria, not observed results or '
    'universal significance levels.'
)
p(
    'The project will also report failure rates, invalid-program rates, trial '
    'evaluation fractions, wall-clock overhead, and memory consumption. A method that '
    'achieves a lower final error by consuming substantially more design computation '
    'will not be presented as unconditionally more efficient. Evaluation cost and total '
    'computational cost will be reported on separate axes.'
)
page('4 Original journal evidence and positioning')
p(
    'The literature basis consists of original journal articles. ALDes [1] treats '
    'metaheuristic design as autoregressive sequence generation and already includes '
    'the accumulation and reuse of design knowledge. Therefore neither algorithm '
    'generation nor continual design alone is a defensible novelty claim for CODA-BBO. '
    'Reinforcement learning within a general search framework [2] and PPO-based '
    'algorithm design [9] also establish that learned design decisions and informative '
    'search features are existing research directions.'
)
p(
    'Cenikj and colleagues [3] examine algorithm-selection generalization under '
    'distribution shift. Their results motivate a strong single-best-solver baseline '
    'and make a seed-only split inadequate for the thesis. Meta-level algorithm '
    'selection [10] further motivates comparisons with ensembles of selectors rather '
    'than only a single selection rule.'
)
p(
    'The 2026 AdaE-SAEA study [8] jointly controls surrogate modeling and infill '
    'selection for expensive multi-objective problems. It is relevant evidence that '
    'multi-component control is already being investigated. Its objective setting '
    'differs from the present single-objective scope. Automated constrained '
    'multi-objective configuration [6] and universal evolutionary generation [7] '
    'likewise delimit the novelty space rather than supply performance claims for '
    'CODA-BBO.'
)
p(
    'OOD research in IJCV [11,13] addresses uncertainty and selective decisions in '
    'visual classification. These papers support the design of diagnostic comparisons '
    'and abstention mechanisms, but their guarantees and empirical performance cannot '
    'be transferred directly to optimization trajectories. Schedule-robust continual '
    'learning [12] motivates order-sensitive evaluation; its classification setting '
    'must remain explicit.'
)
table(
    ['Research strand', 'Existing evidence', 'CODA BBO question'],
    [
        (
            'Generation and design',
            '[1], [2], [7], [9]',
            'When does a structural change pay for itself online?',
        ),
        (
            'Representation and selection',
            '[3], [4], [10]',
            'Can joint program and trajectory information predict transfer loss?',
        ),
        (
            'Adaptive component control',
            '[6], [8]',
            'Can action granularity be selected using risk and remaining budget?',
        ),
        (
            'OOD and selective decisions',
            '[11], [13]',
            'Can abstaining from risky edits improve optimization utility?',
        ),
        (
            'Dynamic and continual behavior',
            '[5], [12]',
            'Can memory and drift handling work across unfavorable task schedules?',
        ),
    ],
    [1.65, 1.5, 3.7],
)
p(
    'The journals include IEEE Transactions on Evolutionary Computation, IEEE '
    'Transactions on Cybernetics, IEEE TPAMI, Springer Machine Learning and IJCV, and '
    'Elsevier Swarm and Evolutionary Computation and Expert Systems with Applications. '
    'No numerical impact-factor or quartile claim is required for the argument.'
)
page('5 Proposed scientific contributions')
h('Contribution one Program conditioned transfer risk')
p(
    'We will learn a joint representation z of the current program, the observed search '
    'history, and the remaining budget. The target will be the additional loss caused '
    'by reusing a design or making a particular change. This differs from using novelty '
    'as a binary synonym for danger. A novel task may still suit the current algorithm; '
    'a familiar-looking task may expose a costly failure mode. The risk model will be '
    'evaluated on its ability to predict those outcomes.'
)
h('Contribution two Cost aware choice of design action')
p(
    'The controller will choose the smallest intervention with positive expected net '
    'utility. Keeping the current program is a valid action. Parameter tuning, '
    'structural editing, and regeneration incur different validation and state-transfer '
    'costs. The controller will compare expected improvement, uncertainty, '
    'objective-call cost, and time cost before allocating a trial. This joint decision '
    'rule is the proposed mechanism to test, rather than merely the combination of '
    'several modules.'
)
h('Contribution three Validated editing with state contracts')
p(
    'A typed domain-specific language will define how operators receive and update '
    'population state. Each edit must preserve compatible state or invoke an explicit '
    'conversion. Invalid compositions will be rejected before objective evaluation. '
    'Candidate validation will test resource bounds, numeric finiteness, dimensional '
    'consistency, and budget behavior. A rejected candidate can leave a useful '
    'evaluated point in the shared archive while its internal state is discarded.'
)
h('Contribution four Memory of benefits and failures')
p(
    'The memory will retain program representations, task descriptors, outcomes, costs, '
    'and reasons for failed transfer. Retrieval will be conditioned on both similarity '
    'and uncertainty. Replay will include failures so that the designer does not '
    'repeatedly propose a harmful edit simply because successful designs dominate the '
    'archive. Forgetting will be measured by revisiting held-out evaluation tasks under '
    'a frozen evaluation protocol.'
)
p(
    'These contributions remain hypotheses. A full related-work check and direct '
    'comparisons will determine whether the joint mechanism provides a publishable '
    'advance. The stage zero code does not establish any of these claims: it contains a '
    'finite program pool, a handcrafted novelty statistic, and heuristic action '
    'triggers.'
)
page('6 Formal learning and decision model')
p(
    'For task k and evaluation t, let H(k,t) be the permitted history, A(k,t) the '
    'current program, and b(k,t) the remaining budget. The representation is z = '
    'encoder(H, A, b). A predictive model estimates the loss difference between an '
    'action and retaining the current design over a fixed future evaluation horizon. '
    'Counterfactual labels will be collected by branching from saved training states, '
    'with all branch costs recorded in the training budget.'
)
h('Optimization objective')
p(
    'The meta-objective will minimize expected normalized anytime loss plus weighted '
    'penalties for objective evaluations used in design, controller runtime, invalid '
    'executions, and catastrophic regressions. The coefficients will be chosen on '
    'validation tasks before testing. Performance and cost will also be reported '
    'separately, because a single weighted score can hide an unfavorable trade-off.'
)
p(
    'At a decision point, an action is eligible only if its predicted improvement '
    'exceeds its uncertainty allowance and estimated cost. A lower-confidence-bound '
    'rule is a useful transparent baseline. A contextual bandit can learn short-horizon '
    'action values before attempting a full sequential reinforcement-learning '
    'controller. PPO will be considered only if the value of long-term credit '
    'assignment is demonstrated.'
)
h('Risk calibration')
p(
    'The model will estimate a probability or interval for harmful transfer, not claim '
    'a distribution-free guarantee under arbitrary shift. Calibration will be tested '
    'using reliability diagrams, proper scoring rules, and empirical risk versus '
    'coverage. Separate calibration data will be reserved by family or task group. A '
    'geometric distance score and a stagnation trigger will remain baselines.'
)
h('Training information boundaries')
p(
    'The optimizer receives only queried objective values, domain bounds, dimensions, '
    'and execution statistics. Known optima and function labels can be used by the '
    'evaluator to score synthetic tasks, but cannot enter the deployed controller. '
    'Meta-training may use supervised transfer labels from controlled rollouts. '
    'Evaluation family labels remain hidden. In a continual stream, updates may use '
    'only data that has already arrived.'
)
h('Budget conservation')
p(
    'For each task, B equals initialization calls plus monitoring calls plus '
    'candidate-trial calls plus ordinary search calls. Candidate rejection cannot '
    'refund evaluations. In the proposed full demonstration with B = 5,000, initial '
    'probing can use 100 calls, monitoring up to 100, and trials up to 500, leaving at '
    'least 4,300 ordinary-search calls if all reserves are used. Unused reserves return '
    'to ordinary search.'
)
page('7 Architecture and executable language')
table(
    ['Module', 'Input and output', 'Implementation plan'],
    [
        (
            'Trajectory encoder',
            'Observed points, values, actions → history representation',
            'Start with invariant summary features; compare a small sequence encoder.',
        ),
        (
            'Program encoder',
            'Typed operator graph → program representation',
            'Compare operator counts, graph embedding, and token sequence models.',
        ),
        (
            'Risk estimator',
            'Joint state → transfer loss and uncertainty',
            'Ensemble regressors followed by calibration on held-out validation groups.',
        ),
        (
            'Action controller',
            'Risk, state, budget → keep or modify',
            'Cost-aware bandit first; sequential policy only after ablation evidence.',
        ),
        (
            'Generator and validator',
            'Conditioned state → valid program',
            'Grammar-masked generation with bounded loops and resource contracts.',
        ),
        (
            'Memory',
            'Design episodes → retrieved experience',
            'Store successes and failures with bounded replay and versioned schemas.',
        ),
    ],
    [1.4, 2.7, 2.75],
)
p(
    'The proposed language will expose initialization, selection, variation, repair, '
    'acceptance, archive update, and stopping operators. Types include bounded point '
    'vectors, populations, fitness arrays, and execution contexts. Dimension and '
    'population-size contracts will prevent compositions that are syntactically legal '
    'but semantically incompatible. No generated program can call an objective outside '
    'the central budget wrapper.'
)
p(
    'A structural edit may substitute an operator, insert a bounded stage, remove a '
    'redundant stage, or change a connection between compatible stages. Generation '
    'starts a new bounded structure within the same language. We will compare these '
    'actions with a finite portfolio whose components and training budget are matched. '
    'That comparison is essential to demonstrate value beyond selecting among a few '
    'predefined methods.'
)
h('State transfer and rollback')
p(
    'Population points and verified evaluations can be reused when semantics are '
    'compatible. Operator-specific state, such as a covariance estimate or surrogate, '
    'must pass a conversion rule or be reinitialized. Rollback restores an earlier '
    'executable state but cannot erase spent objective evaluations. If the objective '
    'has changed, cached fitness values become invalid and must be reevaluated before '
    'use.'
)
p(
    'The pilot uses only three primitive proposal operators and a small fixed set of '
    'compositions. Its validity checks are bounded-length and allowed-operator checks, '
    'not a complete static type system. This deliberately small implementation makes '
    'the evaluation accounting inspectable before a learned generator is introduced.'
)
page('8 Continual learning and drift experiments')
p(
    'The continual version will process tasks sequentially. After task k, the framework '
    'may update its memory and designer using the information observed so far. '
    'Evaluation will use several schedules: blocked families, interleaved families, '
    'gradual mixture changes, and recurrence of earlier families. A frozen designer, a '
    'periodically retrained designer, replay-only learning, and the full memory '
    'mechanism will be compared under equal update resources.'
)
h('Retention and forward transfer')
p(
    'Forward transfer measures the change in performance on an arriving task relative '
    'to an equivalent learner without previous experience. Retention measures '
    'performance on a fixed evaluation bank after additional training. Evaluation-bank '
    'observations must not be replayed into training. The bank will use separate '
    'instances and seeds, and its evaluation cost will be reported separately from '
    'online optimization.'
)
p(
    'Memory capacity will be varied in bytes and episodes. A reservoir strategy will be '
    'compared with diversity-based retrieval and risk-weighted retrieval. Negative '
    'examples will record the prior program, proposed change, observed loss, trial '
    'cost, and uncertainty. If retaining failures offers no advantage over a matched '
    'success-only memory, that component will be removed rather than defended by '
    'intuition.'
)
h('Objective drift')
p(
    'Within-task dynamics will be a separate experiment. The evaluator will introduce '
    'known shifts or changes at hidden times. The controller will receive no change '
    'label. Fixed sentinel points can be reevaluated to detect changes, and the cost of '
    'those calls will count against B. All relevant baselines will receive an '
    'equivalent monitoring budget and cache-invalidation policy.'
)
p(
    'Dynamic performance will be scored against the current objective, using the '
    'currently recommended point rather than a historical best value from a previous '
    'environment. Tracking loss, detection delay, false alarms, recovery evaluations, '
    'and revalidation costs will be reported. Ordinary static best-so-far curves would '
    'be misleading after a change. No dynamic or continual results are claimed for the '
    'included pilot.'
)
page('9 Implemented pilot and its limits')
table(
    ['Capability', 'Executed pilot', 'Full research target'],
    [
        (
            'Representation',
            'Four initial probe statistics',
            'Joint trajectory and program representation',
        ),
        (
            'OOD signal',
            'Frozen standardized feature distance',
            'Calibrated prediction of transfer loss',
        ),
        ('Controller', 'Novelty or stagnation trigger', 'Learned cost-aware action choice'),
        (
            'Program space',
            'Three fixed candidate compositions plus DE',
            'Typed bounded grammar with learned generation',
        ),
        (
            'Reconfiguration',
            'Paired 20-call candidate and control trials',
            'Adaptive trials and compatible state conversion',
        ),
        ('Memory', 'No cross-task update', 'Bounded success and failure memory'),
        (
            'Environment',
            'Static deterministic analytic objectives',
            'Frozen shift, continual streams, and later drift',
        ),
        (
            'Evidence',
            '2,160 runs and software tests',
            'Large independent benchmark and application study',
        ),
    ],
    [1.4, 2.65, 2.8],
)
p(
    'Every method starts from the same 40 uniform probes for a given task and seed. The '
    'best 20 probes initialize the population for population-based methods. All initial '
    'calls count toward the 1,000-call budget. The random-search baseline also benefits '
    'from those probes and then continues sampling uniformly.'
)
p(
    'The primitive DE operator uses rand/1 mutation with binomial crossover probability '
    '0.9 and an initial scale F = 0.7. The local operator samples a Gaussian '
    'displacement from the current population best. The uniform operator samples within '
    'the box. Proposals are clipped to the bounds. These implementations are '
    'transparent baselines; Adaptive-DE is a handcrafted parameter-switching method and '
    'is not JADE, SHADE, or a state-of-the-art DE reproduction.'
)
p(
    'At evaluation checkpoints 200, 400, 600, and 800, the controller checks whether '
    'improvement since the previous checkpoint is at most 1% of the previous best '
    'magnitude. CODA-pilot also responds to a high initial novelty score. A trigger '
    'changes F between 0.45 and 0.85 and reduces the local scale by a factor of 0.65 '
    'with a floor of 0.01. These constants were fixed before the final analysis and '
    'were not optimized on the test results.'
)
page('10 Trial semantics and software verification')
p(
    'On a structural trigger, CODA-pilot selects a candidate different from the current '
    'composition from DE plus local, local plus DE plus local, or DE plus uniform plus '
    'local. Each sequence chooses the proposal operator cyclically. The current and '
    'candidate programs start from copies of the same population, and each receives 20 '
    'objective calls. The state with the better population minimum is retained; ties '
    'retain the current program. All 40 calls are charged.'
)
p(
    'All observed points contribute to the global best-so-far record, including useful '
    'points found by a branch whose population is not retained. The measured incumbent '
    'is the best queried value; it need not be a member of the retained population. '
    'This is legitimate for static deterministic optimization, but the same policy '
    'could not retain stale objective values under drift.'
)
table(
    ['Verification group', 'Implemented assertion', 'Outcome'],
    [
        (
            'Objective definitions',
            'Known shifted optimum has value zero; sampled values are nonnegative.',
            '2 tests passed',
        ),
        (
            'Budget and validity',
            'Budget overrun rejected; invalid points rejected before charging.',
            '2 tests passed',
        ),
        (
            'Program execution',
            'Invalid operators or lengths rejected; proposals remain in the box.',
            '2 tests passed',
        ),
        (
            'Run consistency',
            'Every method reaches its exact budget; recorded incumbent is monotone.',
            '1 test passed',
        ),
        ('Reproducibility', 'Same seed gives identical result and sampled curve.', '1 test passed'),
        (
            'Trial accounting',
            'Forced triggers cause four trials and exactly 160 trial calls.',
            '1 test passed',
        ),
        (
            'Information separation',
            'Reference list excludes held-out families; methods share initial probes.',
            '2 tests passed',
        ),
        (
            'Feature stability',
            'Features invariant to positive affine fitness scaling within tolerance.',
            '1 test passed',
        ),
    ],
    [1.4, 4.1, 1.35],
)
p(
    'All 12 tests passed in the delivered execution. These tests verify important '
    'contracts but do not prove the mathematical validity of the full proposed system. '
    'In particular, no test certifies learned risk calibration, safe transfer under '
    'drift, or continual retention because those components are not implemented.'
)
h('Ablations')
p(
    'No-OOD uses the same structural trial machinery but only the stagnation trigger. '
    'No-edit keeps the novelty-or-stagnation trigger and parameter changes but disables '
    'structural trials. Adaptive-DE uses stagnation-triggered parameter changes without '
    'novelty or edits. These comparisons isolate parts of the heuristic policy, '
    'although changing an ablation also changes subsequent trajectories and '
    'random-number consumption.'
)
page('11 Experimental protocol and scoring')
table(
    ['Protocol item', 'Executed setting'],
    [
        ('Function families', 'Sphere, ellipsoid, Rastrigin, Ackley, Rosenbrock, Griewank'),
        ('Domain and instances', '[-5, 5]^d; three deterministic random shifts in [-1, 1]^d'),
        ('Dimensions and seeds', 'd = 5 and 10; seeds 0 through 9'),
        ('Reference families', 'Sphere, ellipsoid, Rastrigin'),
        ('Held-out families', 'Ackley, Rosenbrock, Griewank'),
        ('Per-run budget', '1,000 calls including 40 initial probes and all trials'),
        (
            'Total test workload',
            '6 families × 2 dimensions × 3 instances × 10 seeds × 6 methods = 2,160 runs',
        ),
        ('Calibration workload', '180 probe sets × 40 evaluations = 7,200 additional calls'),
        ('Controller checkpoints', '200, 400, 600, 800 calls; at most 160 paired-trial calls per run'),
    ],
    [1.65, 5.2],
)
p(
    'These are explicit analytic test functions implemented in pilot.py. They are not '
    'an official COCO or BBOB benchmark run. The shifted optima are inside the domain '
    'and have value zero. For Rosenbrock the internal coordinates add one after '
    'subtracting the shift. Griewank is deliberately restricted to the same box, which '
    'produces a relatively local test and limits conclusions about its standard '
    'wider-domain behavior.'
)
p(
    'Calibration uses separate instances numbered 100 through 129 and separate probe '
    'seeds. For each dimension, 60 reference feature vectors estimate location and '
    'scale; 30 further vectors set the empirical 95th-percentile distance threshold. '
    'The score is the root mean square standardized feature distance, with a 0.05 scale '
    'floor. It is not a posterior probability and has no formal false-alarm guarantee.'
)
h('Primary metric')
p(
    'For each evaluation t from 40 to 1,000, let e(t) be the nonnegative best observed '
    'objective value. The normalized value is log(1 + e(t)) divided by log(1 + e(40)). '
    'The run AUC is the arithmetic mean of these 961 values. Lower is better. The '
    'metric measures progress relative to the common initial probe result and uses a '
    'log scale to reduce domination by large objective magnitudes. It is not a '
    'percentage of the global optimum recovered.'
)
page('12 Statistical analysis and reporting rules')
p(
    'The analysis first averages run AUC across the ten seeds for each family, '
    'dimension, instance, and method. It then averages dimensions and instances within '
    'each family and gives the six families equal weight. This prevents differences in '
    'raw objective scale from dominating the overall summary. Final objective values '
    'are reported separately by family because cross-family raw errors are not directly '
    'comparable.'
)
p(
    'Exploratory 95% intervals use 10,000 paired bootstrap resamples of the six family '
    'means, with bootstrap seed 20261016. The same sampled family indices are used for '
    'all methods. There are only six family clusters, including only three held-out '
    'families. Consequently these intervals are descriptive and too limited to support '
    'broad inferential claims. The hundreds of seed-level runs are not treated as '
    'independent evidence about hundreds of unrelated problem families.'
)
p(
    'The relative AUC reduction against baseline b is 100 × (mean AUC of b minus mean '
    'AUC of CODA-pilot) / mean AUC of b. Positive values favor CODA-pilot; negative '
    'values favor the baseline. This is a ratio of aggregate means, not the mean of '
    'per-run percentages. All chart labels and tables use this same definition.'
)
p(
    'Win, tie, and loss counts use the 36 family-dimension-instance task cells after '
    'seed averaging. Ties use an absolute AUC tolerance of 10^-12. The cells are '
    'descriptive units nested within families. We do not interpret a 36-cell win count '
    'as 36 independent family-level successes.'
)
h('OOD diagnostic rules')
p(
    'Novelty discrimination is evaluated once per task and seed, using the DE records '
    'because the initial probes are common across methods. Family membership defines '
    'the diagnostic label: reference versus held-out. AUROC is computed from the rank '
    'statistic. No threshold is chosen using held-out labels. The threshold flag rates '
    'are also reported. Classification of a family as novel is not evidence that the '
    'current solver would suffer transfer loss.'
)
h('Full study inference')
p(
    'The confirmatory study will preregister its primary comparison and use '
    'hierarchical uncertainty estimates with enough independent task groups. Secondary '
    'comparisons will apply a multiple-comparison correction such as Holm where a valid '
    'test is used. Effect sizes and failure cases will remain visible even when '
    'significance thresholds are not crossed. Anytime assessment guidance in [14] '
    'informs the broader benchmark design.'
)
page('13 Measured aggregate results')
fig('aggregate.png', 'Figure 1. Executed pilot AUC. Error bars are exploratory 95% paired family-bootstrap intervals.')
table(
    ['Method', 'Mean AUC', '95% interval', 'Median time s'],
    [[x.method, f'{x.mean_auc:.4f}', f'[{x.ci_low:.4f}, {x.ci_high:.4f}]', f'{x.median_seconds:.4f}'] for x in summary.itertuples()],
    [1.55, 1.2, 2.5, 1.6],
)
p(
    f"The final benchmark contains {manifest['runs']:,} complete runs and "
    f"{manifest['objective_evaluations']:,} objective calls. Calibration adds "
    "7,200 calls outside the per-task budgets. End-to-end benchmark execution "
    f"took {manifest['elapsed_seconds']:.2f} seconds in the recorded Python "
    "environment. Per-run timing includes initialization, feature calculation, "
    "search, and trial execution; it excludes calibration and analysis. Timing "
    "on cheap analytic objectives is dominated partly by interpreter overhead "
    "and should not be extrapolated to expensive simulations."
)
p(
    'These results compare the delivered implementations only. They do not compare '
    'against an executed ALDes, CMA-ES, SHADE, Bayesian optimizer, or external MetaBBO '
    'implementation. Such baselines are required before any claim of competitive '
    'research performance.'
)
page('14 Measured percentage differences')
fig('percentages.png', 'Figure 2. Relative reduction of mean AUC. A negative value means CODA-pilot is worse than the named baseline.')
table(
    ['Baseline', 'Change %', '95% interval %', 'W T L'],
    [[x.baseline, f'{x.relative_auc_reduction_pct:.2f}', f'[{x.ci_low:.2f}, {x.ci_high:.2f}]', f'{x.wins} / {x.ties} / {x.losses}'] for x in comp.itertuples()],
    [1.5, 1.2, 2.7, 1.45],
)
p(
    "Against DE, the measured relative AUC reduction is "
    f"{vsde.relative_auc_reduction_pct:.2f}%. Against the handcrafted "
    f"Adaptive-DE baseline it is {vsadapt.relative_auc_reduction_pct:.2f}%. "
    f"Against No-OOD it is {vsno.relative_auc_reduction_pct:.2f}%. These "
    "comparisons address different mechanisms and should not be collapsed "
    "into a single headline improvement."
)
p(
    'Any interval spanning zero indicates that the direction is not stable under this '
    'small family-resampling analysis. Even an interval excluding zero would remain '
    'limited by the small, deliberately simple function set. The appropriate conclusion '
    'is a statement about this pilot, not a general superiority claim. The trial-cost '
    'cap and common initialization make the budget comparison inspectable, but they do '
    'not make the baseline suite comprehensive.'
)
page('15 Function level behavior')
fig('convergence.png', 'Figure 3. Mean normalized log-error trajectories. Curves are sampled every 20 calls from evaluation 40; the AUC calculation uses every call.', 6.2)
fig('heatmap.png', 'Figure 4. Family mean AUC after averaging dimensions, shifts, and seeds. Lower values are better.', 5.5)
p(
    'Family-specific behavior matters more than a single average. Easy smooth '
    'objectives, ill-conditioning, multimodality, and curved valleys expose different '
    'weaknesses. A controller that helps only one family can still improve the global '
    'average, so the full study will require explicit family holdouts and a broader '
    'landscape distribution. The curves include improvements discovered during both '
    'accepted and rejected trial branches.'
)
page('16 Final errors and novelty diagnostics')
table(
    ['Family', 'Random', 'DE', 'Adaptive', 'CODA', 'No OOD', 'No edit'],
    [[row['family']] + [f'{row[m]:.3g}' for m in ['Random', 'DE', 'Adaptive-DE', 'CODA-pilot', 'No-OOD', 'No-edit']] for _, row in final.iterrows()],
    [1.25, 0.93, 0.93, 0.93, 0.93, 0.93, 0.93],
)
p(
    'Table above. Median final raw objective error across 60 runs per family and '
    'method. All implemented objectives have a known minimum of zero. Values across '
    'different families use different objective scales and must not be averaged as a '
    'universal error score.'
)
fig('diagnostics.png', 'Figure 5. Initial novelty separation and mean trial activity. Family membership is the diagnostic label; it is not a harmful-transfer label.')
p(
    f"The initial score has family-label AUROC {ood['auroc']:.3f}. The "
    f"threshold flags {ood['reference_flag_rate_pct']:.2f}% of reference "
    f"records and {ood['heldout_flag_rate_pct']:.2f}% of held-out records. "
    f"The diagnostic uses {ood['independent_seed_task_records']} task-seed "
    "records nested in six families. A nominal 95th-percentile calibration "
    "threshold does not imply an observed 5% reference flag rate on new instances."
)
p(
    'The AUROC indicates useful separation in this particular family split, but the '
    'threshold detects fewer than half of the held-out records. Neither result measures '
    'harmful transfer. The next model must predict the cost of retaining or modifying a '
    'specific optimizer, and its action utility must be tested directly.'
)
page('17 Interpretation and limits of the evidence')
p(
    'The pilot establishes that a small reconfiguration mechanism can be executed with '
    'complete objective accounting and analyzed reproducibly. Its most useful result is '
    'not a claim that the proposed framework is finished. It identifies a measurable '
    'gap between a heuristic intervention policy and the stronger thesis goal of '
    'choosing changes according to predicted transfer loss and cost.'
)
p(
    'The aggregate result is favorable relative to DE, but the structural contribution '
    'is less certain: the comparison with No-edit has an interval that crosses zero. '
    'CODA-pilot also has worse median final errors than Adaptive-DE on sphere and '
    'ellipsoid, despite its better aggregate anytime score. These are substantive '
    'limitations, not exceptions to omit.'
)
p(
    'The novelty signal is computed only once from the initial probes. It does not '
    'monitor changing trajectories, condition on program structure, or detect objective '
    'drift. The candidate pool is a small handcrafted collection, so its behavior is '
    'closer to adaptive composition selection than open-ended self-generation. The '
    'local operator has an obvious advantage on some simple landscapes and can be '
    'ineffective on others; success here cannot establish that learned generation is '
    'needed.'
)
p(
    'Trial selection is noisy even in deterministic objectives because each branch uses '
    'stochastic proposals. The control branch is evaluated before the candidate branch, '
    'and random-number streams diverge across methods after shared initialization. '
    'Pairing seeds therefore guarantees common initial probes but not identical '
    'subsequent randomness. A later implementation should examine paired child streams '
    'and repeated trials as sensitivity checks, with every extra call charged.'
)
p(
    'The functions are smooth analytic examples, the two tested dimensions are modest, '
    'and only three shifted instances are used per family. No rotations, noisy '
    'observations, expensive simulators, hidden constraints, or real application data '
    'are included. These restrictions substantially limit external validity. More seeds '
    'cannot replace more independent problem families.'
)
h('Next implementation decision')
p(
    'The next stage should prioritize a stronger benchmark and a transfer-loss dataset '
    'before adding a large neural generator. A fixed portfolio, tuned adaptive DE, and '
    'CMA-ES can reveal whether the present benefit comes from simple operator '
    'complementarity. If novelty contributes little beyond stagnation, the risk model '
    'should be trained on actual counterfactual losses rather than merely adding more '
    'distance features. If editing does not repay its trial cost, a smaller action '
    'space may be the better research direction.'
)
page('18 Full validation design')
table(
    ['Study', 'Controlled comparison', 'Primary outcome'],
    [
        (
            'Frozen task generalization',
            'Family holdouts with no test-time learning',
            'Anytime loss and final target attainment',
        ),
        (
            'Structural value',
            'Full grammar versus equal-cost finite portfolio',
            'Benefit after generation and trial costs',
        ),
        (
            'Risk value',
            'Transfer-risk model versus novelty and stagnation',
            'Action utility and calibration under shift',
        ),
        (
            'Continual behavior',
            'Multiple task schedules and memory budgets',
            'Forward transfer, retention, order sensitivity',
        ),
        (
            'Objective drift',
            'Hidden changes with equal monitoring resources',
            'Tracking error, false alarms, recovery calls',
        ),
        (
            'Application validation',
            'One costly simulator or model-tuning task family',
            'Quality under evaluation and wall-clock caps',
        ),
    ],
    [1.5, 3.1, 2.25],
)
p(
    'A first expanded static campaign can use 24 analytic benchmark functions, five '
    'instances, dimensions 5, 10, and 20, and 20 seeds. This gives 7,200 runs per '
    'method. At a budget of 1,000d per run, the objective-call total is 24 × 5 × 20 × '
    '1,000 × (5 + 10 + 20) = 84 million per method. Ten methods would require 840 '
    'million calls before meta-training, validation, or dynamic experiments.'
)
p(
    'This arithmetic makes a staged compute gate necessary. The expanded study will '
    'begin with fewer seeds to estimate runtime and failure modes, then freeze '
    'configurations and run the full evaluation. Expensive application objectives will '
    'use a separate smaller budget rather than copying the synthetic benchmark count. '
    'Training costs will be recorded independently and amortization will be shown as '
    'the number of future tasks needed to offset those costs.'
)
h('Baseline families')
p(
    'Required baselines include random search, a single best solver selected on '
    'training data, strong DE variants, CMA-ES, a suitable Bayesian optimizer for '
    'expensive low-dimensional tasks, static algorithm selection, a finite dynamic '
    'portfolio, and published automated-design or MetaBBO methods where reproducible '
    'code and matching scope exist. External implementations will retain their '
    'documented settings unless tuning resources are explicitly matched. A failed '
    'reproduction will be reported, not silently substituted with a weaker namesake.'
)
page('19 Ablations and sensitivity analysis')
table(
    ['Ablation', 'What changes', 'What it tests'],
    [
        (
            'No program representation',
            'Keep trajectory features; remove program input',
            'Whether risk is optimizer-specific',
        ),
        (
            'No transfer-risk target',
            'Use distance or stagnation instead',
            'Whether predicted loss adds useful information',
        ),
        ('No structural action', 'Only keep and tune', 'Value beyond parameter adaptation'),
        ('No online edit', 'Generate once at initialization', 'Value of within-run reconfiguration'),
        (
            'No failure memory',
            'Replay successful designs only',
            'Avoidance of repeated negative transfer',
        ),
        ('No continual updates', 'Freeze designer and memory', 'Benefits and costs of online learning'),
        (
            'Matched portfolio',
            'Use a fixed set with equal trial budget',
            'Value of generation beyond selection',
        ),
        ('No cost penalty', 'Optimize improvement alone', 'Whether the controller wastes budget'),
    ],
    [1.55, 2.7, 2.6],
)
p(
    'Sensitivity analysis will vary probe fraction, trial fraction, risk threshold, '
    'action frequency, grammar depth, population size, memory capacity, and objective '
    'cost. These settings will be chosen on validation tasks and then frozen. A broad '
    'search over these choices on the test set would invalidate the intended holdout '
    'comparison.'
)
p(
    'The main budget sensitivity will compare total objective budgets, not merely the '
    'number of ordinary search steps. The runtime sensitivity will simulate or measure '
    'different objective costs to show when controller overhead becomes negligible or '
    'dominant. The grammar sensitivity will distinguish an improvement caused by '
    'additional expressive power from one caused by additional search resources.'
)
h('Mechanistic analysis')
p(
    'For each accepted edit, logs will record the previous program, proposed program, '
    'trigger, predicted risk, trial cost, acceptance criterion, and subsequent outcome. '
    'Representative success and failure episodes will be selected using a predefined '
    'sampling rule. Operator-frequency charts alone will not establish causal utility; '
    'counterfactual branch experiments on training or dedicated analysis tasks will be '
    'needed.'
)
page('20 Application study and resource plan')
p(
    'A suitable application should provide repeatable objective evaluations, a clear '
    'budget, and meaningful variation across tasks. Candidate settings include '
    'simulator parameter calibration or continuous hyperparameter tuning of a modest '
    'machine-learning model. The final choice will depend on access to data and '
    'compute. No unconfirmed industrial dataset, collaborator, or deployment result is '
    'assumed in this proposal.'
)
p(
    'For model tuning, training, validation, and final evaluation data must be '
    'separated. The optimizer observes only validation performance during search; the '
    'final held-out data is used once to assess the selected configuration. Task '
    'distributions can vary by dataset, noise level, or model class, but the split must '
    'prevent near-duplicate tasks from appearing in both meta-training and evaluation.'
)
p(
    'For simulation, the proposal will document deterministic versus stochastic '
    'responses, failure handling, latency, and feasible parameter bounds. A failed '
    'simulation is an observed cost rather than a free retry. Repeated evaluations used '
    'to estimate noise will count against the budget. Where optima are unknown, '
    'reporting will use common targets or best-known references established without '
    'allowing the proposed method privileged information.'
)
h('Compute and engineering')
p(
    'The current pilot uses CPU execution and does not require a GPU. The learned '
    'generator and sequence encoder may require a GPU during training, but deployment '
    'inference should remain small relative to an expensive objective. Resource '
    'requests will be justified by a measured learning curve and compute audit rather '
    'than a fixed claim about hardware speed. The project will preserve configuration '
    'files, model checkpoints, seeds, source versions, and environment specifications.'
)
table(
    ['Resource', 'Planning basis'],
    [
        (
            'CPU benchmark time',
            'Measure cost per evaluation before scaling to 84 million calls per method.',
        ),
        (
            'GPU training',
            'Start with compact encoders and a bandit; expand only when evidence supports it.',
        ),
        ('Storage', 'Compressed trajectories, candidate logs, model versions, and archived manifests.'),
        ('Application budget', 'Separate cap based on simulator or model-training latency.'),
        ('Reproduction reserve', 'Allocate time for independent baseline checks and failed runs.'),
    ],
    [1.65, 5.2],
)
page('21 Work plan risks and expected outputs')
table(
    ['Months', 'Deliverable', 'Gate before progression'],
    [
        (
            '1 to 6',
            'Benchmark infrastructure and stage zero replication',
            'Correct accounting and competitive baseline suite',
        ),
        (
            '7 to 12',
            'Transfer-loss dataset and calibrated risk model',
            'Useful held-out prediction beyond simple features',
        ),
        (
            '13 to 18',
            'Typed generator and state-transfer mechanism',
            'Valid programs and value beyond a portfolio',
        ),
        (
            '19 to 24',
            'Cost-aware online controller and ablations',
            'Benefits survive matched total budgets',
        ),
        (
            '25 to 30',
            'Continual memory and drift studies',
            'Retention and order robustness are measured',
        ),
        (
            '31 to 36',
            'Application study thesis and releases',
            'Reproducible evidence and bounded conclusions',
        ),
    ],
    [0.9, 3.0, 2.95],
)
h('Principal risks')
p(
    'The largest scientific risk is that a strong portfolio or adaptive baseline '
    'matches the full system. That outcome would narrow the contribution toward '
    'reliable risk estimation or evaluation methodology. A second risk is poor risk '
    'calibration under severe shift. The fallback is conservative abstention, explicit '
    'uncertainty reporting, and simpler actions. A third risk is excessive training '
    'cost. Smaller representations, offline datasets, and staged compute gates reduce '
    'that risk.'
)
p(
    'The main engineering risks are invalid programs, incompatible state transfers, and '
    'stale evaluations after drift. A central evaluation wrapper, typed interfaces, '
    'execution limits, and cache versioning address these directly. These controls '
    'guarantee only defined execution properties; they do not guarantee superior '
    'objective performance.'
)
h('Expected outputs')
p(
    'The expected research outputs are a formal problem formulation, a benchmark '
    'protocol for budgeted online algorithm redesign, a risk-conditioned designer, a '
    'continual memory mechanism, and an openly reproducible experimental package where '
    'licensing permits. Possible publication units are the transfer-risk model and '
    'benchmark, validated online generation, and continual or dynamic extensions. '
    'Publication acceptance and numerical improvements cannot be promised in advance.'
)
p(
    'The supervisor decision requested is approval of the scoped research questions and '
    'staged evaluation plan. The pilot supports proceeding to stronger baselines and '
    'transfer-loss modeling. It does not justify treating the full CODA-BBO framework '
    'as an already validated doctoral contribution.'
)
page('22 Reproducibility package and execution')
p(
    'The companion archive contains the complete pilot source, the test suite, analysis '
    'code, raw measurements, figures, environment versions, and source verification '
    'records. The optimization code uses NumPy and pandas; the analysis additionally '
    'uses SciPy and Matplotlib. The document builder uses python-docx. Exact observed '
    'package versions are supplied in requirements.txt.'
)
h('Commands')
for line in [
    'python -m venv .venv',
    'source .venv/bin/activate',
    'python -m pip install -r requirements.txt',
    'python -m unittest -v test_pilot',
    'python pilot.py --out results --seeds 10 --budget 1000',
    'python analyze.py',
]:
    par = p(line)
    par.paragraph_format.space_after = Pt(4)
    par.runs[0].font.name = 'Consolas'
    par.runs[0].font.size = Pt(10)
p(
    'On Windows, activate the virtual environment using the corresponding Scripts '
    'activation command. The source verifier needs internet access; the optimization '
    'experiment and analysis do not. Rerunning the pilot overwrites local result files '
    'in the selected output directory. Scientific values should reproduce within normal '
    'floating-point tolerances in the pinned environment, whereas timing is hardware '
    'dependent.'
)
table(
    ['File', 'Purpose'],
    [
        (
            'pilot.py',
            'Objective definitions, calibration, program executor, budget accounting, experiments',
        ),
        ('test_pilot.py', 'Twelve executable contract and reproducibility tests'),
        ('analyze.py', 'Aggregates, family-bootstrap intervals, percentages, and figures'),
        ('results/runs.csv', 'One record per optimization run including budgets and actions'),
        ('results/curves.npz', 'Sampled best-so-far curves in runs.csv row order'),
        ('results/manifest.json', 'Experiment settings, calibration parameters, and runtime metadata'),
        ('results/sources.json', 'Crossref metadata and DOI resolution audit'),
        ('results/tests.txt', 'Captured software test results'),
        ('figures', 'Five generated plots from the measured results'),
    ],
    [2.1, 4.75],
)
p(
    'The code and results are an inspectable research prototype. They should be '
    'extended through versioned changes and rerun experiments. Replacing a heuristic '
    'component with a learned model changes the method and requires a new evidence '
    'record; it does not retroactively change the meaning of the results reported here.'
)
page('23 DOI verification and reference policy')
p(
    'The reference window uses final issue years from 2022 through 2026 where '
    'available. Early-access dates can precede the issue year: for example [5] has a '
    '2021 DOI and a 2022 issue, while [10] appeared online in 2022 and in an issue in '
    '2023. DOI strings are identifiers, not publication-year filters. Advance-online '
    'records without final pagination are cited without invented page ranges.'
)
p(
    'The audit queries Crossref metadata and resolves each DOI to a publisher endpoint. '
    'HTTP 200 indicates a successful response; IEEE endpoints in this execution '
    'commonly returned HTTP 202. A redirect and publisher response support identifier '
    'validity but do not certify unrestricted full-text access. The archive preserves '
    'exact endpoints, response codes, metadata, and check timestamps. Abstract-level or '
    'metadata-level access is not described as a full-text review.'
)
rows = []
for r in sources:
    rows.append([str(r['id']), r['doi'], str(r.get('crossref_status', 'not obtained')), str(r.get('resolver_status', 'not obtained'))])
table(['Ref', 'DOI', 'Crossref', 'Publisher'], rows, [0.4, 4.8, 0.8, 0.85])
p(
    'The bibliography excludes review and survey articles. Selection is based on '
    'methodological relevance and established specialist journals. No unsupported '
    'numerical journal ranking is assigned. The argument relies on the scope and '
    'findings of specific research articles, not on access model or publisher prestige '
    'alone.'
)
page('24 References')
for idx, r in enumerate(sources):
    if idx == 7:
        page('24 References continued')
    m = r.get('metadata', {})
    authors = m.get('author', [])
    names = ', '.join(((a.get('given', '') + ' ' + a.get('family', '')).strip() for a in authors))
    title = re.sub('<[^>]+>', '', m.get('title', ['Metadata unavailable'])[0])
    journal = m.get('container-title', [''])[0]
    dates = m.get('published-print', m.get('published', {})).get('date-parts', [[2025]])[0]
    year = dates[0]
    if r['id'] == 5:
        year = 2022
    if r['id'] == 10:
        year = 2023
    if r['id'] == 12:
        year = 2026
    if r['id'] == 11:
        year = 2025
    details = []
    if m.get('volume'):
        details.append('vol. ' + m['volume'])
    if m.get('issue'):
        details.append('no. ' + m['issue'])
    if m.get('page') and m['page'] != '1-1':
        details.append(('article ' if r['id'] in (3, 8, 9) else 'pp. ') + m['page'])
    elif m.get('article-number'):
        details.append('article ' + m['article-number'])
    elif not m.get('volume'):
        details.append('advance online publication')
    p(f"[{r['id']}] {names}. {title}. {journal}, {year}" + (', ' + ', '.join(details) if details else '') + '. DOI: ' + r['doi'] + '. https://doi.org/' + r['doi'])
page('Appendix A Objective definitions and algorithm')
p(
    'The implementation defines z = x - s, where s is a reproducible shift in [-1, '
    '1]^d. The box is [-5, 5]^d and all optima have value zero at x = s. These formulas '
    'specify the benchmark completely and do not imply equivalence to official BBOB '
    'transformations.'
)
table(
    ['Family', 'Implemented formula'],
    [
        ('Sphere', 'sum_i z_i^2'),
        ('Ellipsoid', 'sum_i 10^[4(i-1)/(d-1)] z_i^2'),
        ('Rastrigin', '10d + sum_i [z_i^2 - 10 cos(2 pi z_i)]'),
        ('Ackley', '-20 exp[-0.2 sqrt(mean_i z_i^2)] - exp[mean_i cos(2 pi z_i)] + 20 + e'),
        ('Rosenbrock', 'With w = z + 1: sum_(i=1)^(d-1) [100(w_(i+1) - w_i^2)^2 + (w_i - 1)^2]'),
        ('Griewank', 'sum_i z_i^2 / 4000 - product_i cos(z_i / sqrt(i)) + 1'),
    ],
    [1.3, 5.55],
)
h('Pilot procedure')
for line in [
    '1  Evaluate 40 shared probes through the central budget wrapper.',
    '2  Compute four probe features and the frozen novelty flag.',
    '3  Keep the best 20 probes as the initial population.',
    '4  Until the total objective budget is exhausted, generate and evaluate proposals.',
    '5  At each checkpoint, compute stagnation and the method-specific trigger.',
    '6  If permitted, tune parameters and select a different candidate composition.',
    '7  Copy the current state and evaluate control and candidate for 20 calls each.',
    '8  Retain the better population state while preserving all observed incumbent improvements.',
    '9  Save the final metrics, sampled curve, action counts, and exact evaluation count.',
]:
    p(line)
p(
    'The four features are fitness-distance correlation, standardized fitness skewness, '
    'the standardized 90th-minus-50th percentile, and the mean absolute adjacent '
    'difference in the standardized probe values. The fourth feature depends on probe '
    'order; it is a simple dispersion statistic, not a spatial landscape measure. A '
    'learned representation should test whether it provides useful information rather '
    'than assuming all four features are necessary.'
)
page('Appendix B Split results and accounting')
split = runs.groupby(['split', 'method']).auc.mean().unstack()
table(
    ['Method', 'Reference AUC', 'Held out AUC'],
    [[m, f"{split.loc['reference', m]:.4f}", f"{split.loc['held-out', m]:.4f}"] for m in ['Random', 'DE', 'Adaptive-DE', 'CODA-pilot', 'No-OOD', 'No-edit']],
    [2.2, 2.3, 2.35],
)
for splitname in ['reference', 'held-out']:
    b = split.loc[splitname, 'DE']
    v = split.loc[splitname, 'CODA-pilot']
    p(
        f'On {splitname} families, the relative AUC reduction against DE is '
        f'{100 * (b - v) / b:.2f}%. Each split contains three families. This '
        'is a descriptive split analysis without a separate confirmatory '
        'hypothesis test.'
    )
cc = runs[runs.method == 'CODA-pilot']
p(
    f'CODA-pilot spent a mean of {cc.trial_evals.mean():.2f} calls per run '
    'on paired candidate and control trials, equivalent to '
    f'{100 * cc.trial_evals.mean() / 1000:.2f}% of its task budget. The maximum '
    'permitted trial fraction was 16%. Initial probing used 4% for every '
    'method. Trial calls remain useful objective observations even when the '
    'candidate is rejected.'
)
h('Formal target for the learned controller')
p(
    'Let L(A, H, h) be the future normalized loss over horizon h when program A '
    'continues from history H. A training label for an intervention a is Delta(a) = L(A '
    'after a, H, h) - L(A, H, h). A positive value means harmful transfer or '
    'modification. Separate matched rollouts on training states estimate this label. '
    'Their cost belongs to meta-training, not to an unreported free oracle.'
)
p(
    'A proposed action utility is U(a) = -E[Delta(a) | z] - lambda_e C_e(a) - lambda_t '
    'C_t(a) - beta sigma(a), with keep as the reference action. C_e is the estimated '
    'objective-call cost normalized by remaining budget, C_t is normalized runtime, and '
    'sigma is predictive uncertainty. All coefficients and normalizations must be fixed '
    'on validation tasks. This is a research specification, not the equation used by '
    'the heuristic pilot.'
)
p(
    'For continual training, replay and regularization terms will be added to the '
    'transfer prediction and action-value losses. They will be assessed through '
    'controlled ablations rather than presumed to improve retention. The delivered '
    'tests and results remain evidence only for the executed static prototype.'
)
# Clean up paragraph borders before saving the document.
for root in [doc.styles.element, doc.element]:
    for border in list(root.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
out = Path('CODA_BBO_English_Proposal.docx')
doc.save(out)
print(out, 'paragraphs', len(doc.paragraphs), 'tables', len(doc.tables))
