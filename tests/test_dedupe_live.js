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
console.log('PASS real data deduplication + different-job and ambiguity regressions');
