'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('index.html','utf8');
const scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
assert(scripts.length>=2,'embedded app JS missing');
const code=scripts.at(-1)[1];
const begin=code.indexOf('const FIELDS ='),end=code.indexOf('function visible()');
assert(begin>0&&end>begin,'missing deduplication functions');
const context={
 window:{STARTER_DATA:{jobs:[]}},localStorage:{getItem:()=>null,setItem:()=>{}},
 document:{},URL,Date,console
};
vm.runInNewContext(code.slice(begin,end)+'\nthis._dedupe=dedupe;this._isGeneric=isGeneric;',context,{timeout:10000});
const jobData=JSON.parse(fs.readFileSync('data/jobs.json','utf8')).jobs;
const matches=jobData.filter(x=>String(x.company).includes('삼천리'));
assert(matches.length>=5,'live data no longer contains the targeted collision');
const real=context._dedupe(matches);
console.log('삼천리 source records:',matches.length, 'deduplicated:',real.length,
            'groups:',real.map(g=>({title:g.title,ids:g.ids,dates:[g.start_date,g.end_date]})));
assert.strictEqual(real.length,1,'삼천리 2027년 신입 공채 must display once');
assert(real[0].ids.length>=5,'all original source IDs should survive merging');
const example={
 source:'jasoseol',company:'한빛전기',title:'2026 하반기 발전설비 설계 엔지니어 모집',
 positions:'발전설비 설계',company_type:'중견기업',employment:'신입',
 start_date:'2026-10-02',end_date:'2026-10-14',result_date:'',test_date:'',
 url:'https://jasoseol.com/recruit/999991',id:'test-a'
};
const variant={...example,title:'2026 하반기 회계 재무 담당자 모집',
 positions:'회계 재무',url:'https://jasoseol.com/recruit/999992',id:'test-b'};
const distinct=context._dedupe([example,variant]);
assert.strictEqual(distinct.length,2,'same company / dates but different jobs must remain separate');
const otherGeneric={...example,id:'test-c',source:'jobkorea',title:'공채달력 일정 · 원본 공고 확인 필요',positions:'',url:'https://www.jobkorea.co.kr/starter/calendar'};
const ambiguous=context._dedupe([example,variant,otherGeneric]);
assert.strictEqual(ambiguous.length,3,'ambiguous calendar entry must not be merged arbitrarily');

const sameLinkOld={...example,id:'legacy-1',end_date:'2026-10-14',
                   url:'https://jasoseol.com/recruit/999991',title:'발전설비 설계 엔지니어 모집'};
const sameLinkNew={...example,id:'jasoseol-999991',end_date:'2026-10-13',
                   end_datetime:'2026-10-14T00:00+09:00',
                   title:'2026 하반기 발전설비 설계 엔지니어 모집 발전사업부'};
const changed=context._dedupe([sameLinkOld,sameLinkNew]);
assert.equal(changed.length,1,'same source URL must merge even if deadlines conflict');
assert.equal(changed[0].end_date,'2026-10-13','confirmed midnight deadline must win');
assert.equal(changed[0].end_datetime,'2026-10-14T00:00+09:00','precise source deadline must be retained');
const full=context._dedupe(jobData), seenBySourceId=new Map(), conflicts=[];
for(const g of full){
  for(const l of g.links||[]){
    const u=new URL(l.url);
    const jas=u.hostname.endsWith('jasoseol.com')&&u.pathname.match(/^\/recruit\/(\d+)\/?$/i);
    const job=u.hostname.endsWith('jobkorea.co.kr')&&u.pathname.match(/^\/Recruit\/GI_Read\/(\d+)\/?$/i);
    const key=jas?'jasoseol:'+jas[1]:job?'jobkorea:'+job[1]:null;
    if(!key)continue;
    if(seenBySourceId.has(key)&&seenBySourceId.get(key)!==g.id)conflicts.push([key,seenBySourceId.get(key),g.id]);
    seenBySourceId.set(key,g.id);
  }
}
console.log('LIVE_DEDUPE_AUDIT raw='+jobData.length+' merged='+full.length+
            ' canonical_jobs='+seenBySourceId.size+' canonical_conflicts='+conflicts.length,
            'samples='+JSON.stringify(conflicts.slice(0,7)));
assert.deepEqual(conflicts,[],'same canonical job appears in multiple merged groups');
console.log('PASS real data deduplication, canonical identity, midnight preference, different-job checks');

