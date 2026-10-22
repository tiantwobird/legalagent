"""Create an explicitly reviewed, source-anchored 50-task Legal Agent RL pilot set.

Inputs: data/labor_subset.jsonl, or --corpus to override.
This is educational evaluation data, not a legal-opinion or lawyer-certified dataset.
"""
import argparse, collections, json, pathlib, random

from ..paths import DATA, TASKS

BASE = TASKS
DEFAULT_CORPUS = DATA/'labor_subset.jsonl'
parser=argparse.ArgumentParser()
parser.add_argument('--corpus',type=pathlib.Path,default=DEFAULT_CORPUS)
args=parser.parse_args()
corpus=[json.loads(x) for x in args.corpus.open(encoding='utf-8') if x.strip()]
index={(r['law_id'],r['article_number']):r for r in corpus}
assert len(index)==len(corpus)
DATE='2024-06-01'
TASKS=[]

def A(law,n,anchor):
    return (law,n,anchor)
C='labor_contract_law'; E='labor_contract_law_regulation'; L='labor_law'; D='labor_dispute_arbitration_law'; J='labor_dispute_interpretation_1'

FIXED_SPLIT={}
def add(kind,prompt,refs,points,issues,notes='',missing=None,difficulty='easy',fixed_split=None):
    i=len(TASKS)+1
    evidence=[]
    for law,n,anchor in refs:
        if (law,n) not in index:
            raise ValueError(f'missing {law}:{n}')
        r=index[(law,n)]
        if anchor not in r['text']:
            raise ValueError(f'{i} bad anchor {law}:{n}: {anchor}')
        assert r['effective_from']<=DATE, (i,law,n)
        evidence.append({
          'article_id':f'{law}:{n}', 'law_title':r['law_title'],
          'version_id':r['version_id'], 'effective_from':r['effective_from'],
          'source_url':r['source_url'],'text_sha256':r['text_sha256'],
          'supporting_quote':anchor
        })
    tid=f'LABOR_{i:03d}'
    if fixed_split:
        FIXED_SPLIT[tid]=fixed_split
    TASKS.append({
      'task_id':tid,
      'task_type':kind, 'difficulty':difficulty,
      'jurisdiction':'CN', 'applicable_date':DATE,
      'prompt':prompt.strip()+' 请基于2024年6月1日适用的法律，先检索法规，再给出简洁的结论、必要条件和条文ID；如信息不足，请指出缺失事实，不得编造。',
      'gold_article_ids':list(dict.fromkeys(x['article_id'] for x in evidence)),
      'gold_issues':issues,
      'expected_answer_points':points,
      'missing_facts':missing or [],
      'qualification':notes,
      'source_evidence':evidence,
      'review':{'source_anchor_verified':True,'review_method':'assistant_manual_substantive_review_plus_programmatic_exact_quote_matching','independent_human_legal_expert_review':'pending','intended_use':'RL pilot; not legal advice'}
    })

# Direct retrieval (15): narrowly scoped verifiable queries.
add('direct_retrieval','用工后未立即签书面劳动合同，法律规定最晚何时应补签？', [A(C,10,'自用工之日起一个月内订立书面劳动合同')],['已建立劳动关系而未同时签约的，应在用工之日起一个月内订立书面劳动合同。'],['书面合同期限'])
add('direct_retrieval','劳动合同期限为两年时，法定试用期最多约定几个月？',[A(C,19,'一年以上不满三年的，试用期不得超过二个月')],['两年合同试用期不得超过二个月。'],['试用期上限'])
add('direct_retrieval','如何判断试用期工资的法定下限？',[A(C,20,'不得低于用人单位所在地的最低工资标准')],['不低于本单位相同岗位最低档工资或者合同约定工资的80%，且不低于所在地最低工资标准。'],['试用期工资下限'])
add('direct_retrieval','专项技术培训约定服务期，违约金的法定上限与分摊规则是什么？',[A(C,22,'违约金的数额不得超过用人单位提供的培训费用')],['违约金总额不能高于培训费用，实际主张不高于服务期尚未履行部分分摊的培训费用。'],['培训服务期','违约金上限'])
add('direct_retrieval','哪些人员可以成为竞业限制对象？期限最长多久？',[A(C,24,'不得超过二年')],['竞业限制人员限高级管理人员、高级技术人员和其他负有保密义务人员；期限不得超过二年。'],['竞业限制对象','竞业限制期限'])
add('direct_retrieval','正式员工主动辞职与试用期员工主动辞职，通常分别需要提前几日通知？',[A(C,37,'劳动者在试用期内提前三日通知用人单位')],['通常提前三十日书面通知；试用期提前三日通知。'],['主动离职通知期限'])
add('direct_retrieval','劳动者严重违反合法有效的用人单位规章制度，主要应查哪一法条？',[A(C,39,'严重违反用人单位的规章制度的')],['劳动合同法第三十九条列有严重违反规章制度作为用人单位解除劳动合同的事由之一。'],['严重违纪解除'])
add('direct_retrieval','企业因员工不胜任工作并已培训、调岗后仍不胜任，解除劳动合同的通知要求主要规定在哪条？',[A(C,40,'经过培训或者调整工作岗位，仍不能胜任工作的')],['满足法定条件时需提前三十日书面通知或者额外支付一个月工资。'],['不胜任解除','通知或代通知金'])
add('direct_retrieval','劳动合同法在哪条规定孕期、产期、哺乳期等情形对第四十条和第四十一条解除有特别限制？',[A(C,42,'女职工在孕期、产期、哺乳期的')],['第四十二条规定特定保护对象不得依第四十条、第四十一条解除；并非对全部解除事由的一概豁免。'],['特殊保护','解除限制'])
add('direct_retrieval','经济补偿的工作年限如何折算？不足六个月怎么算？',[A(C,47,'不满六个月的，向劳动者支付半个月工资的经济补偿')],['每满一年一个月工资；六个月以上不满一年按一年；不足六个月按半个月。具体工资基数另须依法确定。'],['经济补偿年限'])
add('direct_retrieval','公司解除劳动合同后，应在多久内办理档案和社会保险关系转移手续？',[A(C,50,'在十五日内为劳动者办理档案和社会保险关系转移手续')],['公司应出具解除或终止证明，并在十五日内办理相关转移手续。'],['离职证明','转移期限'])
add('direct_retrieval','劳务派遣劳动者与用工单位同类岗位人员的劳动报酬有什么原则？',[A(C,63,'被派遣劳动者享有与用工单位的劳动者同工同酬的权利')],['被派遣劳动者享有同工同酬权利，应遵循相同劳动报酬分配办法。'],['劳务派遣同工同酬'])
add('direct_retrieval','非全日制用工是否必须签署书面劳动合同？',[A(C,69,'非全日制用工双方当事人可以订立口头协议')],['非全日制用工双方可以订立口头协议。'],['非全日制口头协议'])
add('direct_retrieval','劳动争议申请仲裁的一般时效期间是多长？',[A(D,27,'劳动争议申请仲裁的时效期间为一年')],['一般时效为一年，并存在时效中断、中止和拖欠劳动报酬期间的特别规则。'],['仲裁时效'])
add('direct_retrieval','《劳动法》对工作日延长工时、休息日不能补休、法定节假日工作的加班工资最低倍数分别是什么？',[A(L,44,'不低于工资的百分之一百五十'),A(L,44,'不低于工资的百分之二百'),A(L,44,'不低于工资的百分之三百')],['相应标准不低于150%、200%、300%，休息日情形以不能安排补休为前提。'],['加班工资倍数','补休条件'])

# Fact application (20): each has constrained facts to avoid invented missing evidence.
add('fact_application','张某2024年1月1日开始全日制工作，公司至2024年3月10日仍未与他签书面劳动合同，双方无拒签争议。是否涉及二倍工资责任？',[A(C,10,'自用工之日起一个月内订立书面劳动合同'),A(C,82,'超过一个月不满一年未与劳动者订立书面劳动合同')],['超过一个月未签书面劳动合同，可能依法承担二倍工资责任；具体起算与截止还应核对实施条例。'],['未签书面合同','二倍工资'],difficulty='medium')
add('fact_application','2023年1月1日起某员工持续在公司全日制工作，直至2024年2月仍未签书面劳动合同。根据实施条例，满一年时形成何种法律后果？',[A(E,7,'视为自用工之日起满一年的当日已经与劳动者订立无固定期限劳动合同')],['用工满一年未签书面合同，依法视为满一年当日已经订立无固定期限劳动合同，并须补订书面合同；二倍工资区间另按规定确定。'],['满一年未签约','视为无固定期限'],difficulty='medium')
add('fact_application','公司与员工签订一年固定期限劳动合同，却约定四个月试用期。单就试用期时长是否合法？',[A(C,19,'一年以上不满三年的，试用期不得超过二个月')],['一年合同对应试用期不得超过二个月，四个月超过上限。'],['违法约定试用期'])
add('fact_application','某岗位的最低档月工资和劳动合同约定工资均为6000元，试用期仅发4000元。即使所在地最低工资低于4000元，这一支付标准是否合理？',[A(C,20,'劳动合同约定工资的百分之八十')],['试用期工资4000元同时低于相同岗位最低档工资以及合同约定工资6000元的80%（4800元），不符合法定下限要求。'],['试用期工资比例'])
add('fact_application','公司招聘新员工时要求交纳2000元“上岗保证金”，离职才退。该做法有何合规问题？',[A(C,9,'不得要求劳动者提供担保'),A(C,84,'以担保或者其他名义向劳动者收取财物的')],['不得要求劳动者担保或收取财物；涉嫌违法收取保证金，存在责令退还及法定处罚风险。'],['招聘保证金','禁止收取财物'],difficulty='medium')
add('fact_application','单位要求新员工交出身份证原件由人事部门保管直到试用期结束。是否被法律允许？',[A(C,9,'不得扣押劳动者的居民身份证和其他证件'),A(C,84,'扣押劳动者居民身份证等证件的')],['不得扣押身份证等证件；存在返还和行政处理风险。'],['身份证扣押'])
add('fact_application','企业与刘某在3月20日签劳动合同，约定4月1日上岗且实际4月1日开始用工。劳动关系从何时建立？',[A(C,7,'用人单位自用工之日起即与劳动者建立劳动关系'),A(C,10,'劳动关系自用工之日起建立')],['劳动关系自4月1日实际用工之日起建立，不因提前签约而提前建立。'],['劳动关系建立时间'])
add('fact_application','单位以完成业绩为由强制员工无偿加班，员工不同意，公司宣称无需支付任何加班费。应核查哪些义务？',[A(C,31,'不得强迫或者变相强迫劳动者加班')],['不得强迫或变相强迫加班；安排加班应依国家有关规定支付加班费。'],['强迫加班','加班费'])
add('fact_application','用人单位已经连续拖欠到期工资，劳动者因此提出解除劳动合同。就解除依据和经济补偿应查询什么规则？',[A(C,38,'未及时足额支付劳动报酬的'),A(C,46,'劳动者依照本法第三十八条规定解除劳动合同的')],['未及时足额支付劳动报酬属于劳动者可依第三十八条解除的情形；因此解除符合条件时应支付经济补偿。'],['欠薪解除','经济补偿'],difficulty='medium')
add('fact_application','正式员工决定辞职，书面提前30日通知公司，公司仅以“未批准”为由称不能离职。原则上应如何分析？',[A(C,37,'劳动者提前三十日以书面形式通知用人单位，可以解除劳动合同')],['依法提前三十日书面通知可解除劳动合同，法条并未将公司批准作为该路径的要件。'],['辞职通知','无需批准'])
add('fact_application','公司以经营困难为由，拟依据劳动合同法第四十一条裁减一位仍处孕期的女职工。要检查哪项禁止性规定？',[A(C,42,'女职工在孕期、产期、哺乳期的')],['第四十二条限制对孕期等人员依据第四十、四十一条解除；不应将其纳入以第四十一条为依据的裁减。'],['孕期保护','经济性裁员'],difficulty='medium')
add('fact_application','公司以“员工不胜任”为由当日解除，但从未培训或调整岗位。只据第四十条第二项，解除条件是否已经齐备？',[A(C,40,'经过培训或者调整工作岗位，仍不能胜任工作的')],['尚未满足该项所要求的培训或调岗后仍不能胜任的条件，不能仅凭一次不胜任即当然适用该项解除。'],['不胜任解除要件'],difficulty='medium')
add('fact_application','员工严重违反已合法制定并公示的规章制度，事实、严重程度均有可靠证据。公司可从哪条寻找解除依据？',[A(C,39,'严重违反用人单位的规章制度的')],['可考虑第三十九条第二项的解除事由，仍应遵守适用的通知工会等程序要求。'],['严重违纪','解除事由'],difficulty='medium')
add('fact_application','单位先提出协商解除劳动合同，劳动者表示同意，双方依法达成解除协议。一般应否支付经济补偿？',[A(C,36,'用人单位与劳动者协商一致，可以解除劳动合同'),A(C,46,'用人单位依照本法第三十六条规定向劳动者提出解除劳动合同')],['由用人单位提出并协商一致解除时，属于应支付经济补偿的法定情形。'],['协商解除','补偿触发条件'])
add('fact_application','单位违法解除劳动合同，员工希望继续履行，且客观上仍可以继续履行。劳动合同法规定的优先处理路径是什么？',[A(C,48,'劳动者要求继续履行劳动合同的，用人单位应当继续履行')],['员工要求继续履行且能够继续履行时，用人单位应继续履行劳动合同。'],['违法解除','继续履行'])
add('fact_application','单位违法解除劳动合同，劳动者明确不要求继续履行。应以什么标准主张赔偿金？',[A(C,48,'劳动者不要求继续履行劳动合同'),A(C,87,'经济补偿标准的二倍向劳动者支付赔偿金')],['在违法解除前提下，劳动者不要求继续履行的，按第四十七条经济补偿标准二倍计算违法解除赔偿金。'],['违法解除','赔偿金'],difficulty='medium')
add('fact_application','两年固定期限劳动合同届满，公司提出以更低工资续签，劳动者拒绝。公司称一律无需补偿。应重点核查什么例外？',[A(C,44,'劳动合同期满的'),A(C,46,'用人单位维持或者提高劳动合同约定条件续订劳动合同')],['终止固定期限合同一般涉及经济补偿；若用人单位维持或提高条件续订而劳动者拒绝，才属于条文所述例外；降低工资通常不符合该例外。'],['合同期满','续约条件','经济补偿'],difficulty='medium')
add('fact_application','某公司要求普通行政员工签竞业限制协议，但该员工既不属于高管或高级技术人员，也不负有保密义务。如何分析适格性？',[A(C,24,'其他负有保密义务的人员')],['竞业限制对象有法定范围，给定事实下该员工不属于该范围；不能简单将全部员工列为竞业限制对象。'],['竞业限制对象'])
add('fact_application','劳务派遣员工和用工单位同岗位员工工作内容相同，但派遣员工仅因身份被采用明显不同的报酬分配办法。应核查何原则？',[A(C,63,'实行相同的劳动报酬分配办法')],['被派遣劳动者依法享有同工同酬权利，同类岗位应实行相同的劳动报酬分配办法。'],['派遣同工同酬'])
add('fact_application','员工与单位发生欠薪争议，不愿继续私下协商，希望进入劳动争议解决程序。依法能否直接申请劳动仲裁而不强制先调解？',[A(D,5,'不愿调解、调解不成或者达成调解协议后不履行的')],['可不先达成调解；不愿调解或调解不成等情形可依法申请劳动仲裁，诉讼另依法律规则。'],['劳动仲裁程序'])

# Multi-article reasoning (10): verify the link between provisions, not only citations.
add('multi_article','陈某2024年1月1日开始工作，公司直到2024年4月1日才补签书面劳动合同。假定期间一直依法存在全日制劳动关系且并非员工拒签，应核查二倍工资的触发条件和起止日期。',[A(C,10,'自用工之日起一个月内订立书面劳动合同'),A(C,82,'每月支付二倍的工资'),A(E,6,'起算时间为用工之日起满一个月的次日')],['用工超过一个月未签书面劳动合同触发二倍工资责任；按实施条例第六条从满一个月的次日到补订合同前一日计算适用区间。'],['书面合同期限','二倍工资区间'],difficulty='hard')
add('multi_article','周某2023年1月1日开始全日制工作，截至2024年2月1日一直没有书面劳动合同，公司称“只要以后补签就不产生满一年时的后果”。如何评价？',[A(C,82,'超过一个月不满一年未与劳动者订立书面劳动合同'),A(E,7,'满一年的当日已经与劳动者订立无固定期限劳动合同')],['依法存在满一年未签书面合同的视为无固定期限劳动合同后果，且此前法定期间存在二倍工资责任；后续补签不应直接抹去既有期间责任。'],['满一年未签约','二倍工资','无固定期限'],difficulty='hard')
add('multi_article','公司2024年违法解除吴某劳动合同。吴某不要求恢复劳动关系，在公司已工作满3年，假定赔偿金基数月工资为8000元且不涉及三倍社平工资封顶。主要应引用什么条文？按给定前提赔偿金金额多少？',[A(C,48,'劳动者不要求继续履行劳动合同'),A(C,47,'每满一年支付一个月工资的标准'),A(C,87,'经济补偿标准的二倍')],['违法解除且不要求继续履行，应支付按经济补偿标准二倍计算的赔偿金；满3年、工资基数8000元对应3×8000×2=48000元。'],['违法解除赔偿','经济补偿年限','数额计算'],difficulty='hard')
add('multi_article','王某2022年1月1日至2024年1月1日签两年固定期限劳动合同，期满单位拒绝续签，王某此前月工资均为10000元且不涉及工资封顶，是否涉及经济补偿，按已给事实大致如何折算？',[A(C,44,'劳动合同期满的'),A(C,46,'终止固定期限劳动合同的'),A(C,47,'每满一年支付一个月工资的标准')],['合同期满终止且由公司拒绝续签，属于依法需要经济补偿的典型情形；满两年按两个月工资、即20000元的给定基数折算。'],['合同期满','经济补偿','年限折算'],difficulty='hard')
add('multi_article','公司称员工无法胜任工作，已进行培训后员工仍不能胜任，公司计划按第四十条解除。请说明合法解除的通知/代通知金要求以及是否涉及经济补偿。',[A(C,40,'额外支付劳动者一个月工资后'),A(C,46,'用人单位依照本法第四十条规定解除劳动合同的')],['满足第四十条法定事由时，须提前30日书面通知或额外支付一个月工资；依据第四十条解除一般应支付经济补偿。'],['不胜任解除','通知或代通知金','经济补偿'],difficulty='hard')
add('multi_article','用人单位持续未及时发放工资，劳动者明确依劳动合同法第三十八条解除后拟申请劳动仲裁。请分别说明解除依据、补偿规则和一般仲裁时效。',[A(C,38,'未及时足额支付劳动报酬的'),A(C,46,'劳动者依照本法第三十八条规定解除劳动合同的'),A(D,27,'时效期间为一年')],['工资未及时足额支付可构成第三十八条解除事由；符合条件时应支付经济补偿；一般仲裁时效一年，但拖欠劳动报酬与时效中断等有特别规则。'],['欠薪解除','经济补偿','仲裁时效'],difficulty='hard')
add('multi_article','员工因解除合同争议提起劳动仲裁，公司掌握辞退依据和处理决定但拒不提供。请分析用人单位证据责任和拒绝提供证据的风险。',[A(D,6,'用人单位掌握管理的，用人单位应当提供'),A(J,44,'用人单位负举证责任')],['与争议相关且由单位掌握的材料应提供，否则存在不利后果；对辞退、解除等决定引发的争议，用人单位负举证责任。'],['单位举证','拒不提交材料'],difficulty='hard')
add('multi_article','劳动者主张自己在普通工作日被安排延时加班，却只有微信工作通知截图；公司持有考勤系统完整记录但拒绝提供。应分别核查加班工资标准和举证责任规则。',[A(L,44,'延长工作时间的，支付不低于工资的百分之一百五十'),A(J,42,'用人单位掌握加班事实存在的证据')],['工作日延长工作时间涉及不低于150%的工资报酬标准；劳动者一般对加班事实负举证责任，但能证明用人单位掌握相关证据且对方不提供时，用人单位承担不利后果。'],['加班工资标准','加班事实举证'],difficulty='hard')
add('multi_article','2023年11月劳动者与公司订立有效竞业限制约定，2024年1月解除劳动合同后公司连续三个整月因自身原因未按约支付竞业补偿，劳动者已经履行相应义务。劳动者可考虑什么法律救济？',[A(C,23,'在竞业限制期限内按月给予劳动者经济补偿'),A(J,38,'因用人单位的原因导致三个月未支付经济补偿')],['竞业限制期间用人单位应按月给予经济补偿；因单位原因连续三个月未支付的，劳动者可请求解除竞业限制约定。'],['竞业限制补偿','三个月未支付','请求解除约定'],difficulty='hard')
add('multi_article','劳务派遣单位向劳动者收取入职服务费，用工单位又拒绝向该派遣员工支付其安排的加班费。需分别核查哪两个主体的什么义务？',[A(C,60,'劳务派遣单位和用工单位不得向被派遣劳动者收取费用'),A(C,62,'支付加班费、绩效奖金')],['劳务派遣单位和用工单位均不得向被派遣劳动者收取费用；用工单位负有支付加班费的法定义务。'],['派遣收费','用工单位加班费'],difficulty='hard')

# Insufficient-information cases (5): calibrated answer, no legal overclaim.
add('insufficient_information','公司只说员工“经常迟到”，想当天立即解除劳动合同，但没有提供规章制度、公布情况、迟到次数或证据。能否断言公司可以依据严重违纪立即解除？',[A(C,39,'严重违反用人单位的规章制度的'),A(C,4,'应当将直接涉及劳动者切身利益的规章制度和重大事项决定公示')],['不能仅凭“经常迟到”断言满足严重违纪解除条件；需要核查规章合法性、告知/公示、严重程度及证据。'],['严重违纪','事实不足'],missing=['合法有效的规章制度及其公示','迟到次数与严重程度','客观证据'],difficulty='hard')
add('insufficient_information','一名员工说自己“从年初开始没签劳动合同”，希望你直接报出截至2024年6月1日的二倍工资准确金额，未提供具体用工日期、补签情况和各月工资。可以直接计算吗？',[A(C,82,'每月支付二倍的工资'),A(E,6,'截止时间为补订书面劳动合同的前一日')],['不能直接给出准确金额；应先确认用工起始、书面合同签署时间、月工资及期间事实；可先说明二倍工资责任的法定区间规则。'],['二倍工资','必要事实不足'],missing=['用工确切日期','是否及何时补签','各月工资数据','劳动关系类型与特殊事实'],difficulty='hard')
add('insufficient_information','公司说员工“身体不适，工作不了”，拟立刻无补偿辞退。只有这句话，没有病情、医疗期或岗位安排信息。能否确认可以合法解除？',[A(C,40,'在规定的医疗期满后不能从事原工作'),A(C,42,'在规定的医疗期内的')],['不能断言可立即辞退；应核实法定医疗期是否届满、是否不能胜任原工作及另行安排工作等条件，医疗期内还有相关解除限制。'],['医疗期','解除条件不足'],missing=['医疗期起止','工作能力与安排岗位情况','通知和解除理由'],difficulty='hard')
add('insufficient_information','员工称过去经常加班，公司不付加班费，要求你断定其劳动仲裁一定获胜；但没有具体加班时段、考勤或补休情况。应该如何回答？',[A(L,44,'休息日安排劳动者工作又不能安排补休'),A(J,42,'劳动者主张加班费的，应当就加班事实的存在承担举证责任')],['不能断言仲裁必胜；需区分工作日/休息日/法定节假日、补休情况、加班事实证据及公司掌握的相关证据。'],['加班费','证据不足'],missing=['具体加班时间','加班类别','休息日是否补休','考勤或工作安排证据'],difficulty='hard')
add('insufficient_information','劳动者说“我发现权益受损已经一年多了，还能仲裁吗？”，但未说明争议类型、劳动关系是否存续、是否向公司主张过权利。能直接认定时效过期吗？',[A(D,27,'仲裁时效，因当事人一方向对方当事人主张权利')],['不能简单断言时效已过；一般时效一年，但应考虑知道/应知时间、时效中断、中止以及劳动关系存续期间拖欠劳动报酬的特别规则。'],['仲裁时效','中断中止','事实不足'],missing=['争议性质','知道或应当知道侵害时间','权利主张或救济记录','劳动关系是否存续'],difficulty='hard')

# =====================================================================
# 扩展 test 集（2026-10）：在原 5 题基础上补 25 题，使 frozen test = 30。
# 全部为 free 法条（或与既有 gold 互补），引文逐字取自 data/labor_subset.jsonl。
# 复核状态与原有 50 题一致：助理实质复核 + 程序化逐字比对；独立专家复核 pending。
# =====================================================================

# --- direct_retrieval +6 ---
add('direct_retrieval','劳务派遣公司只和我签了一年合同。派遣单位与被派遣劳动者的合同期限，法律有什么要求？',
 [A(C,58,'应当与被派遣劳动者订立二年以上的固定期限劳动合同')],
 ['劳务派遣单位应当与被派遣劳动者订立二年以上的固定期限劳动合同','并按月支付劳动报酬'],
 ['劳务派遣','合同期限'],difficulty='easy',fixed_split='test')
add('direct_retrieval','我在餐厅做服务员，按小时计酬，平均每天4小时、每周20小时。这算全日制还是非全日制？非全日制是怎么定义的？',
 [A(C,68,'平均每日工作时间不超过四小时')],
 ['非全日制用工以小时计酬为主','一般平均每日工作时间不超过四小时，每周累计不超过二十四小时'],
 ['非全日制','工时'],difficulty='easy',fixed_split='test')
add('direct_retrieval','我做非全日制保洁，公司说工资两个月结一次。非全日制用工的工资结算周期有上限吗？',
 [A(C,72,'劳动报酬结算支付周期最长不得超过十五日')],
 ['非全日制小时计酬不得低于当地最低小时工资标准','劳动报酬结算支付周期最长不得超过十五日'],
 ['非全日制','工资支付'],difficulty='easy',fixed_split='test')
add('direct_retrieval','公司赶订单，要求我们每天加班，一个月累计超过60小时。法律对延长工作时间有上限吗？',
 [A(L,41,'每月不得超过三十六小时')],
 ['一般每日不得超过一小时','特殊原因需要延长的，每日不得超过三小时','每月不得超过三十六小时'],
 ['加班','工时上限'],difficulty='easy',fixed_split='test')
add('direct_retrieval','我试用期工资是转正工资的70%。试用期工资的法定下限是多少？',
 [A(E,15,'不得低于本单位相同岗位最低档工资的80%')],
 ['不得低于本单位相同岗位最低档工资的80%，或不得低于劳动合同约定工资的80%','并不得低于用人单位所在地的最低工资标准'],
 ['试用期','工资'],difficulty='easy',fixed_split='test')
add('direct_retrieval','公司裁员要给我经济补偿。计算月工资时，奖金、津贴、补贴算不算进去？',
 [A(E,27,'按照劳动者应得工资计算')],
 ['经济补偿的月工资按劳动者应得工资计算','包括计时或计件工资以及奖金、津贴和补贴等货币性收入','低于当地最低工资标准的按最低工资标准计算','工作不满12个月的按实际工作月数计算平均工资'],
 ['经济补偿','计算基数'],difficulty='medium',fixed_split='test')

# --- fact_application +10 ---
add('fact_application','我在试用期第2个月被公司辞退，公司只说“不合适”，不肯说明具体理由。这样解除合法吗？公司要做什么？',
 [A(C,21,'应当向劳动者说明理由')],
 ['试用期内，除劳动者有第39条和第40条第一项、第二项规定的情形外，用人单位不得解除劳动合同','在试用期解除劳动合同的，应当向劳动者说明理由'],
 ['试用期解除','说明理由'],difficulty='medium',fixed_split='test')
add('fact_application','我在一家公司做派遣工已经两年，岗位是长期存在的主营业务岗位，公司一直用劳务派遣。这样合规吗？',
 [A(C,66,'存续时间不超过六个月')],
 ['劳务派遣只能用于临时性、辅助性或者替代性岗位','临时性岗位指存续时间不超过六个月的岗位','辅助性岗位是为主营业务岗位提供服务的非主营业务岗位'],
 ['劳务派遣','三性岗位'],difficulty='medium',fixed_split='test')
add('fact_application','公司要裁掉30人，占职工总数15%，直接发通知让下周走人。经济性裁员在程序上有什么要求？',
 [A(C,41,'提前三十日向工会或者全体职工说明情况')],
 ['裁减20人以上，或不足20人但占职工总数10%以上的，需提前三十日向工会或全体职工说明情况并听取意见','裁减方案应向劳动行政部门报告','应优先留用较长期限固定期限合同、无固定期限合同、家庭无其他就业人员等人员'],
 ['经济性裁员','程序','优先留用'],difficulty='hard',fixed_split='test')
add('fact_application','离职时公司一直不给我解除劳动合同的书面证明，导致新公司无法办理入职。公司要承担什么责任？',
 [A(C,89,'由劳动行政部门责令改正')],
 ['用人单位应在解除或终止劳动合同时出具书面证明','未出具的由劳动行政部门责令改正','给劳动者造成损害的，应当承担赔偿责任'],
 ['解除证明','赔偿责任'],difficulty='medium',fixed_split='test')
add('fact_application','公司拖欠我三个月工资，向劳动监察投诉后仍然逾期不付。除了补发工资，还能主张加付赔偿吗？',
 [A(C,85,'百分之五十以上百分之一百以下')],
 ['由劳动行政部门责令限期支付劳动报酬','逾期不支付的，责令按应付金额50%以上100%以下的标准加付赔偿金'],
 ['欠薪','加付赔偿金'],difficulty='medium',fixed_split='test')
add('fact_application','我没提前30天通知就离职，公司说项目因此延误，要我赔偿损失。法律上我需要负责吗？',
 [A(C,90,'给用人单位造成损失的，应当承担赔偿责任')],
 ['劳动者违反本法规定解除劳动合同，给用人单位造成损失的，应当承担赔偿责任','违反保密义务或竞业限制造成损失的，同样承担赔偿责任'],
 ['违法解除','劳动者赔偿'],difficulty='medium',fixed_split='test')
add('fact_application','我做非全日制小时工，公司说要先试用一个月、试用期工资打八折。这样约定有效吗？',
 [A(C,70,'非全日制用工双方当事人不得约定试用期')],
 ['非全日制用工双方当事人不得约定试用期'],
 ['非全日制','试用期'],difficulty='easy',fixed_split='test')
add('fact_application','我因病休了6个月医疗期，回公司后原岗位已有人，公司想解除合同。需要满足什么条件、履行什么程序？',
 [A(L,26,'医疗期满后，不能从事原工作也不能从事由用人单位另行安排的工作')],
 ['患病或非因工负伤，医疗期满后不能从事原工作，也不能从事用人单位另行安排的工作','用人单位可以解除，但应提前三十日以书面形式通知劳动者本人'],
 ['医疗期','解除条件'],difficulty='hard',fixed_split='test')
add('fact_application','我在小公司做前台，月薪1800元，当地最低工资2200元。公司说包吃住所以可以低一些，合法吗？',
 [A(L,48,'用人单位支付劳动者的工资不得低于当地最低工资标准')],
 ['国家实行最低工资保障制度','用人单位支付劳动者的工资不得低于当地最低工资标准','最低工资具体标准由省、自治区、直辖市人民政府规定'],
 ['最低工资'],difficulty='easy',fixed_split='test')
add('fact_application','我怀孕7个多月，公司仍安排我上夜班和加班。我可以拒绝吗？',
 [A(L,61,'不得安排其延长工作时间和夜班劳动')],
 ['不得安排孕期女职工从事第三级体力劳动强度和孕期禁忌从事的劳动','对怀孕七个月以上的女职工，不得安排延长工作时间和夜班劳动'],
 ['女职工保护','孕期'],difficulty='easy',fixed_split='test')

# --- multi_article +7 ---
add('multi_article','公司把我们的派遣合同拆成好几份短期协议，岗位还是原来的长期岗位。这种“连续用工拆短期合同”的做法合规吗？派遣只能在什么岗位使用？',
 [A(C,59,'不得将连续用工期限分割订立数个短期劳务派遣协议'),A(C,66,'只能在临时性、辅助性或者替代性的工作岗位上实施')],
 ['派遣单位应与用工单位订立劳务派遣协议，约定岗位、人员数量、期限、报酬等','用工单位不得将连续用工期限分割订立数个短期劳务派遣协议','劳务派遣只能在临时性、辅助性或者替代性岗位上实施'],
 ['劳务派遣','协议拆分','三性岗位'],difficulty='hard',fixed_split='test')
add('multi_article','我签了竞业限制协议，离职后公司一直没给补偿。协议还有效吗？我可以主张多少补偿？',
 [A(J,36,'按照劳动者在劳动合同解除或者终止前十二个月平均工资的30%按月支付经济补偿'),A(C,23,'在竞业限制期限内按月给予劳动者经济补偿')],
 ['约定竞业限制但未约定经济补偿，劳动者履行了竞业限制义务，可要求按离职前十二个月平均工资的30%按月支付','该30%低于劳动合同履行地最低工资标准的，按最低工资标准支付','用人单位应按月给予经济补偿'],
 ['竞业限制','经济补偿'],difficulty='hard',fixed_split='test')
add('multi_article','仲裁裁决书下来后，公司说是终局裁决。我作为劳动者还能去法院起诉吗？期限多久？',
 [A(D,47,'仲裁裁决为终局裁决'),A(D,48,'自收到仲裁裁决书之日起十五日内向人民法院提起诉讼')],
 ['追索劳动报酬、工伤医疗费、经济补偿或赔偿金，不超过当地月最低工资标准十二个月金额的争议，以及执行国家劳动标准在工作时间、休息休假、社会保险等方面的争议，为终局裁决','劳动者对终局裁决不服的，可自收到裁决书之日起十五日内向人民法院提起诉讼'],
 ['终局裁决','起诉期限'],difficulty='medium',fixed_split='test')
add('multi_article','公司已经三个月不发工资，还说不许我离职。我可以马上走人并要求补偿吗？',
 [A(L,32,'用人单位未按照劳动合同约定支付劳动报酬或者提供劳动条件'),A(C,38,'未及时足额支付劳动报酬的')],
 ['用人单位未按劳动合同约定支付劳动报酬或提供劳动条件，劳动者可以随时通知解除劳动合同','未及时足额支付劳动报酬的，劳动者可以解除劳动合同'],
 ['即时解除','欠薪'],difficulty='medium',fixed_split='test')
add('multi_article','公司实行单休，每周只让我休一天，国庆还安排上班且不给补休。休息休假有哪些法定要求？',
 [A(L,38,'用人单位应当保证劳动者每周至少休息一日'),A(L,40,'用人单位在下列节日期间应当依法安排劳动者休假')],
 ['用人单位应当保证劳动者每周至少休息一日','元旦、春节、国际劳动节、国庆节等法定节日期间应当依法安排劳动者休假'],
 ['休息休假','法定节假日'],difficulty='medium',fixed_split='test')
add('multi_article','我怀孕7个月，孩子出生后还在哺乳期，公司一直安排夜班。孕期和哺乳期分别有什么保护？',
 [A(L,61,'不得安排其延长工作时间和夜班劳动'),A(L,63,'不得安排女职工在哺乳未满一周岁的婴儿期间')],
 ['怀孕七个月以上的女职工，不得安排延长工作时间和夜班劳动','哺乳未满一周岁婴儿期间，不得安排第三级体力劳动强度、哺乳期禁忌劳动，也不得安排延长工作时间和夜班劳动'],
 ['女职工保护','孕期','哺乳期'],difficulty='medium',fixed_split='test')
add('multi_article','公司一直没给我缴社保。我可以因此解除劳动合同吗？用人单位在社保上有什么法定义务？',
 [A(L,72,'用人单位和劳动者必须依法参加社会保险，缴纳社会保险费'),A(C,38,'未依法为劳动者缴纳社会保险费的')],
 ['用人单位和劳动者必须依法参加社会保险、缴纳社会保险费','未依法为劳动者缴纳社会保险费的，劳动者可以解除劳动合同'],
 ['社会保险','被迫解除'],difficulty='medium',fixed_split='test')

# --- insufficient_information +2 ---
add('insufficient_information','公司拖欠我工资好几个月了，我能拿到多少赔偿？',
 [A(C,85,'逾期不支付的，责令用人单位按应付金额'),A(L,50,'不得克扣或者无故拖欠劳动者的工资')],
 ['不能直接给出赔偿金额；需先确认欠薪月数与金额','逾期仍不支付才涉及按应付金额50%以上100%以下加付赔偿金','工资不得克扣或无故拖欠'],
 ['欠薪','赔偿金额'],missing=['拖欠的月数与具体金额','是否已向劳动行政部门投诉','是否已解除劳动合同'],difficulty='hard',fixed_split='test')
add('insufficient_information','公司说效益不好要裁员，让我下周走人。我能拿多少补偿？',
 [A(C,41,'生产经营发生严重困难'),A(E,27,'按照劳动者应得工资计算')],
 ['不能直接给出补偿数额；需先确认是否属于经济性裁员的法定情形、是否履行法定程序','经济补偿按工作年限计算，月工资按应得工资（含奖金、津贴、补贴）计算'],
 ['经济性裁员','经济补偿'],missing=['裁减人数与占职工总数的比例','是否履行提前三十日说明与报告程序','工作年限与解除前十二个月平均工资'],difficulty='hard',fixed_split='test')

assert len(FIXED_SPLIT)==25, len(FIXED_SPLIT)

assert len(TASKS)==75, len(TASKS)
assert collections.Counter(t['task_type'] for t in TASKS)=={'direct_retrieval':21,'fact_application':30,'multi_article':17,'insufficient_information':7}
assert len({t['prompt'] for t in TASKS})==75
assert len({t['task_id'] for t in TASKS})==75
# Distinct and non-overlapping split for an INTEGRATION/SMOKE SET ONLY, not a reliable scientific hold-out benchmark.
split = {'train':[], 'dev':[], 'test':[]}
for typ,seed,ntrain,ndev in [('direct_retrieval',101,10,3),('fact_application',102,14,4),('multi_article',103,7,2),('insufficient_information',104,4,1)]:
    group=[t for t in TASKS if t['task_type']==typ and t['task_id'] not in FIXED_SPLIT]
    rng=random.Random(seed);rng.shuffle(group)
    for i,t in enumerate(group):
        subset='train' if i<ntrain else ('dev' if i<ntrain+ndev else 'test')
        t['split']=subset
        split[subset].append(t)
for t in TASKS:
    if t['task_id'] in FIXED_SPLIT:
        t['split']=FIXED_SPLIT[t['task_id']]
        split[t['split']].append(t)
assert {k:len(v) for k,v in split.items()}=={'train':35,'dev':10,'test':30}, {k:len(v) for k,v in split.items()}

def write_jsonl(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(''.join(json.dumps(obj,ensure_ascii=False)+'\n' for obj in rows),encoding='utf-8')

write_jsonl(BASE/'tasks_all_reviewed.jsonl',TASKS)
for label,rs in split.items():
    write_jsonl(BASE/f'tasks_{label}_labeled.jsonl',rs)
    # Agent-visible dataset MUST NOT include labels/citations/evidence.
    write_jsonl(BASE/f'tasks_{label}_prompts_only.jsonl',[
      {k:t[k] for k in ['task_id','prompt','jurisdiction','applicable_date']} for t in rs
    ])
summary={'total':len(TASKS),'counts_by_type':dict(collections.Counter(t['task_type'] for t in TASKS)),
'split_counts':{k:len(v) for k,v in split.items()},
'law_coverage':dict(collections.Counter(e['law_title'] for t in TASKS for e in t['source_evidence'])),
'article_ids_used':len(set(tid for t in TASKS for tid in t['gold_article_ids'])),
'review_status':'assistant manual review and exact source quote checks; independent legal expert review PENDING',
'fixed_applicable_date':DATE,
'known_limitations':['2024-only snapshot evaluation; this is not a comprehensive historical law database',
'2025 labor dispute judicial interpretation (II) not included; avoid post-2025 questions',
'not validated by an independent licensed PRC lawyer',
'30-question frozen test set; still too small for strong generalization claims']}
(BASE/'audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
