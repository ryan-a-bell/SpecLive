/* SpecLive simulated projection engine. Zero external services, all candidate outputs provisional. */
(function(){'use strict';
const demoSessions={
 'cloud':{name:'Cloud and edge operations',id:'DEMO-CLOUD-EDGE',turns:[
 ['Facilitator','What functions need to remain available when the network is unavailable?'],
 ['Operator','The system must continue critical operations when the network goes down.'],
 ['Architect','Our current concept puts all processing in the cloud.'],
 ['Facilitator','Does that cloud-only model include mission-critical operations during an outage?'],
 ['Operator','We must keep basic situational awareness and alerting available offline.'],
 ['Architect','Advanced analytics can wait until connectivity returns. Basic functions could process locally.'],
 ['Facilitator','How do we protect the data stored locally during the outage?'],
 ['Security lead','All operational data stored locally must be encrypted at rest.'],
 ['Operator','Once connected again, we need queued operational reports synchronized with headquarters.'],
 ['Facilitator','Who will define and accept what counts as critical operation?'],
 ['Operator','The operations team will define critical functions and approve acceptance criteria.'],
 ['Architect','We need to verify the edge processing limits before committing to an offline performance target.']
 ]},
 'recovery':{name:'Service recovery acceptance',id:'DEMO-RECOVERY-30S',turns:[
 ['Facilitator','What is the end-to-end recovery objective following a communications outage?'],
 ['Operator','We need end-to-end service restored within thirty seconds of an outage.'],
 ['Engineer','The current design takes about two minutes to reconnect.'],
 ['Operator','Thirty seconds must be treated as the target requirement.'],
 ['Facilitator','Does thirty seconds apply to radio link recovery or full service restoration?'],
 ['Engineer','We can meet thirty seconds for link recovery, but not end-to-end service yet.'],
 ['Operator','Full end-to-end service must be restored within thirty seconds.'],
 ['Engineer','We could provide degraded operation within thirty seconds and full service within two minutes.'],
 ['Operator','No. Full service must be restored within thirty seconds, not degraded operation.'],
 ['Facilitator','Who will validate this at acceptance testing?'],
 ['Engineer','The integration team will measure end-to-end recovery and the operator will approve the result.']
 ]}
};
const topics=[
 {id:'OPS',name:'Operational continuity',hint:'critical functions, availability, mission',patterns:[/operat|mission|service|availability|basic|critical/i]},
 {id:'CON',name:'Connectivity & outages',hint:'network loss, link and reconnection',patterns:[/network|connect|offline|outage|radio link|reconnect/i]},
 {id:'EDGE',name:'Edge processing',hint:'local compute and degraded mode',patterns:[/locall|edge|offline|processing|degraded/i]},
 {id:'CLOUD',name:'Cloud analytics',hint:'cloud-dependent and delayed analysis',patterns:[/cloud|analytic|headquarters|synchron/i]},
 {id:'DATA',name:'Data lifecycle',hint:'retention, protection, synchronization',patterns:[/data|stor|queue|encrypt|reports|synchron/i]},
 {id:'PERF',name:'Performance targets',hint:'timing, throughput and measurable thresholds',patterns:[/seconds|minutes|latenc|perform|target|limits|restored within/i]},
 {id:'SEC',name:'Security & assurance',hint:'protect data, access, threat model',patterns:[/security|encrypt|protect|access control/i]},
 {id:'VER',name:'Verification & acceptance',hint:'measure, test, approver, criteria',patterns:[/verif|validat|accept|measur|approv|criteri|integration team/i]}
];
const relations=[['OPS','CON','depends on'],['OPS','EDGE','supported by'],['EDGE','CLOUD','operating modes'],['EDGE','DATA','produces'],['CON','PERF','constrains'],['DATA','SEC','protected by'],['PERF','VER','verified by'],['OPS','VER','accepted by'],['CLOUD','CON','depends on']];
const reqRules=[
 {id:'REQ-OFFLINE',topic:'OPS',kind:'explicit',title:'Critical functions remain operational offline',statement:'The system shall maintain identified critical operational functions during a network outage.',rx:/\b(must|need|shall|required)\b.{0,70}\b(critical operations|offline|network goes down|network is unavailable|basic situational awareness)/i},
 {id:'REQ-EDGE',topic:'EDGE',kind:'derived',title:'Basic functions permitted locally',statement:'The system shall support basic functions with local processing when disconnected; details require confirmation.',rx:/\b(basic functions.*locally|basic .*offline|situational awareness.*offline|critical functions.*local)/i},
 {id:'REQ-CLOUD-ANALYTICS',topic:'CLOUD',kind:'derived',title:'Advanced analytics deferred during outage',statement:'Advanced analytics may be deferred until external connectivity returns.',rx:/\b(advanced analytics.*wait|analytics.*connectivity returns)/i},
 {id:'REQ-ENCRYPT',topic:'SEC',kind:'explicit',title:'Encrypt local operational data',statement:'The system shall encrypt operational data stored locally at rest.',rx:/\b(encrypted? at rest|stored locally.*encrypt|data.*encrypt)/i},
 {id:'REQ-SYNC',topic:'DATA',kind:'explicit',title:'Synchronize deferred reports',statement:'The system shall synchronize queued operational reports after connectivity is restored.',rx:/\b(queued operational reports synchronized|reports.*synchron|synchron.*headquarters)/i},
 {id:'REQ-RECOVERY',topic:'PERF',kind:'explicit',title:'30-second end-to-end recovery',statement:'The system shall restore full end-to-end service within 30 seconds of a communications outage.',rx:/\b(end.to.end service restored within thirty seconds|end.to.end recovery.*thirty seconds|full end.to.end service.*thirty seconds|full service must be restored within thirty seconds|thirty seconds must.*target)/i},
 {id:'REQ-ACCEPT',topic:'VER',kind:'explicit',title:'Acceptance authority and verification',statement:'Recovery and continuity criteria shall be measured by the integration team and approved by designated operational authority.',rx:/\b(integration team.*measur|operations team.*acceptance criteria|operator.*approv.*result)/i},
 {id:'REQ-LOCAL-STORE',topic:'DATA',kind:'derived',title:'Local buffering during disconnect',statement:'Hypothesis: locally generated operational data may require buffering during loss of connectivity.',rx:/\b(queued operational reports|data stored locally|synchron.*connectivity)/i}
];
const quotes=[
 {id:'ISS-CLOUD',title:'Cloud-only vs offline execution',type:'potential_conflict',risk:96,question:'Which critical operations must execute locally during a network outage, and which can remain cloud-dependent?'},
 {id:'ISS-RECOVERY',title:'Recovery target vs demonstrated capability',type:'feasibility_gap',risk:100,question:'What technical or scope change closes the gap between the 30-second target and current two-minute recovery?'},
 {id:'ISS-ALTERNATIVE',title:'Degraded-mode fallback rejected',type:'rejected_alternative',risk:76,question:'With degraded operation rejected, what design change or decision path enables full recovery within 30 seconds?'}
];
const fmtTime=ms=>{const s=Math.max(0,Math.round((Number(ms)||0)/1000));return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')};
function normalizeEvidence(r,i,sid){return {evidence_id:String(r.evidence_id||r.id||`EVD-IMPORT-${String(i+1).padStart(3,'0')}`),session_id:String(r.session_id||sid),text:String(r.text||''),speaker_name:String(r.speaker_name||r.speaker_id||'Unknown speaker'),speaker_id:String(r.speaker_id||''),start_ms:Number(r.start_ms||0),end_ms:Number(r.end_ms||r.start_ms||0),match_status:String(r.match_status||'imported'),clock_status:String(r.clock_status||'unknown'),origin:String(r.origin||'imported'),source_transcript_id:r.source_transcript_id||null,revision:Number(r.revision||1)}}
function demoEvidence(id,count){const session=demoSessions[id]||demoSessions.cloud;return session.turns.slice(0,count).map((t,i)=>({evidence_id:`EVD-${session.id}-${String(i+1).padStart(3,'0')}`,session_id:session.id,text:t[1],speaker_name:t[0],speaker_id:`SPK-${t[0].toUpperCase().replace(/\s/g,'-')}`,start_ms:i*6700+300,end_ms:i*6700+5900,match_status:'time_aligned',clock_status:'shared_session',origin:'scripted_scenario',revision:1,source_transcript_id:`TXT-${i+1}`}))}
function evidence(state){const base=state.mode==='import'?state.importEvidence:demoEvidence(state.scenario,state.step);return [...base,...state.custom].map((x,i)=>normalizeEvidence(x,i,state.session_id))}
function project(state){const ev=evidence(state);const byId=new Map(ev.map(x=>[x.evidence_id,x]));let t=topics.map(topic=>{const refs=ev.filter(e=>topic.patterns.some(re=>re.test(e.text))).map(e=>e.evidence_id);return {...topic,evidence_ids:refs,status:refs.length>=2?'discussed':refs.length?'mentioned':'not covered',score:Math.min(100,refs.length*48)}});
 const req=reqRules.map(r=>{const refs=ev.filter(e=>!/[?]\s*$/.test(e.text)&&r.rx.test(e.text)).map(e=>e.evidence_id);return {...r,evidence_ids:refs,lifecycle:'candidate',origin:'transparent_demo_rules'}}).filter(r=>r.evidence_ids.length);
 const has=id=>req.some(r=>r.id===id),evidRx=rx=>ev.filter(e=>rx.test(e.text)).map(e=>e.evidence_id);
 let issues=[];const cloudClaim=evidRx(/\b(all processing in the cloud|cloud.only|all processing.*cloud|everything.*cloud)/i);if(has('REQ-OFFLINE')&&cloudClaim.length){let ids=[...req.find(r=>r.id==='REQ-OFFLINE').evidence_ids,...cloudClaim];const edge=req.find(r=>r.id==='REQ-EDGE');if(edge)ids.push(...edge.evidence_ids);issues.push({...quotes[0],evidence_ids:[...new Set(ids)],status:edge?'proposed_interpretation':'unresolved',explanation:edge?'Later evidence supports a local/cloud split, but an authority must confirm the exceptions.':'Two statements imply incompatible behavior during outages unless cloud processing has exceptions.'})}
 const current=evidRx(/current design takes about two minutes|not end.to.end.*yet|cannot meet.*end.to.end/i);if(has('REQ-RECOVERY')&&current.length)issues.push({...quotes[1],evidence_ids:[...new Set([...req.find(r=>r.id==='REQ-RECOVERY').evidence_ids,...current])],status:'unresolved',explanation:'A performance feasibility gap is not a conflicting stakeholder requirement.'});
 const alt=evidRx(/could provide degraded operation|degraded operation within/i),rejected=evidRx(/no\. full service|not degraded operation/i);if(alt.length&&rejected.length)issues.push({...quotes[2],evidence_ids:[...alt,...rejected],status:'rejected_proposal',explanation:'A proposed fallback was rejected. It must not be treated as an approved alternative.'});
 let questions=[];for(const issue of issues){const review=state.issueDecisions[issue.id];if(review&&review.decision==='resolved')continue;questions.push({id:`Q-${issue.id}`,kind:'risk',topic:null,risk:issue.risk,coverage:22,title:issue.question,why:issue.explanation,evidence_ids:issue.evidence_ids,source_id:issue.id});}
 const topicQuestions={OPS:'Which mission functions are essential during an outage?',CON:'What outage types and connectivity assumptions are in scope?',EDGE:'What compute and storage can operate at the edge?',CLOUD:'Which analytics genuinely require cloud connectivity?',DATA:'What data must persist or synchronize after an outage?',PERF:'What measurable timing and performance limits apply?',SEC:'What security controls apply to local and synchronized data?',VER:'Who owns acceptance criteria, and how will they be verified?'};
 for(const topic of t.filter(x=>x.status!=='discussed'))questions.push({id:`Q-TOP-${topic.id}`,kind:'coverage',topic:topic.id,risk:topic.id==='SEC'?48:27,coverage:topic.status==='not covered'?98:59,title:topicQuestions[topic.id],why:topic.status==='not covered'?'No matching discussion evidence yet.':'Only a limited mention; coverage is not evidence of completeness.',evidence_ids:topic.evidence_ids,source_id:topic.id});
 questions=questions.filter(q=>!state.asked.includes(q.id)&&!state.dismissed.includes(q.id)).map(q=>{let score=state.strategy==='risk'?.83*q.risk+.17*q.coverage:state.strategy==='coverage'?.25*q.risk+.75*q.coverage:.65*q.risk+.35*q.coverage;return {...q,score:Math.round(score)}}).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id));
 const covered=t.filter(x=>x.status!=='not covered').length;
 const gates={reviewer:!!state.reviewer.trim(),requirements:req.length>0,decisions:req.length>0&&req.every(r=>['approved','revised','rejected'].includes(state.reviews[r.id]?.decision)),issues:issues.every(i=>state.issueDecisions[i.id]?.decision==='resolved'),approved:req.some(r=>['approved','revised'].includes(state.reviews[r.id]?.decision)),provenance:req.every(r=>r.evidence_ids.length&&r.evidence_ids.every(id=>byId.has(id)))};
 return {evidence:ev,byId,topics:t,requirements:req,issues,questions,covered,gates,ready:Object.values(gates).every(Boolean)};
}
function freshState(){return {version:1,scenario:'cloud',session_id:demoSessions.cloud.id,mode:'demo',step:0,importEvidence:[],custom:[],strategy:'balanced',asked:[],dismissed:[],reviews:{},issueDecisions:{},reviewer:'',audit:[],selected:null,sealed:null,revision:1,graphLayer:'topics',graphMode:'graph',topicView:'list',tab:'requirements'}}
function cleanImport(data){if(!data||!Array.isArray(data.evidence)||data.schema!=='speclive.evidence.v0.1')throw Error('Expected F04 JSON with schema speclive.evidence.v0.1 and evidence[]');if(data.evidence.length>2000)throw Error('Maximum 2,000 evidence events');const ids=new Set(),sid=String(data.session_id||'');if(!sid)throw Error('F04 session_id is missing');const cleaned=data.evidence.map((r,i)=>normalizeEvidence(r,i,sid));for(const r of cleaned){if(!r.text||!r.evidence_id||ids.has(r.evidence_id))throw Error('Missing/duplicate evidence ID or text');if(r.session_id!==sid)throw Error('Cross-session evidence in import');if(!Number.isFinite(r.start_ms)||!Number.isFinite(r.end_ms)||r.start_ms>r.end_ms)throw Error('Invalid time span');ids.add(r.evidence_id)}return {session_id:sid,evidence:cleaned}}
function escapeHTML(value){return String(value??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function download(name,data,type='application/json'){const a=document.createElement('a');const blob=new Blob([data],{type});a.href=URL.createObjectURL(blob);a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),6000)}
function citeList(ids,byId){return ids.map(id=>byId.get(id)).filter(Boolean)}
window.SpecEngine={demoSessions,topics,relations,reqRules,fmtTime,freshState,project,download,escapeHTML,cleanImport,citeList};
})();
