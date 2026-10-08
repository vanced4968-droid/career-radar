'use strict';
const fs=require('fs'),assert=require('assert'),{JSDOM,VirtualConsole}=require('jsdom');
async function main(){
  const html=fs.readFileSync('index.html','utf8');
  const jobs=JSON.parse(fs.readFileSync('data/jobs.json','utf8'));
  const runtimeErrors=[];
  const vc=new VirtualConsole();
  vc.on('jsdomError',e=>runtimeErrors.push(e.message));
  const dom=new JSDOM(html,{
    url:'https://vanced4968-droid.github.io/career-radar/',
    runScripts:'dangerously',
    pretendToBeVisual:true,
    virtualConsole:vc,
    beforeParse(window){
      window.fetch=async()=>({ok:true,json:async()=>jobs});
      window.alert=()=>{};
      window.confirm=()=>true;
      window.addEventListener('error',e=>runtimeErrors.push(e.message));
      window.addEventListener('unhandledrejection',e=>runtimeErrors.push('promise: '+e.reason));
    }
  });
  await new Promise(resolve=>setTimeout(resolve,350));
  const d=dom.window.document;
  const nav=d.querySelector('#calendarGrid');
  assert(nav && nav.querySelectorAll('.day[data-date]').length>=28,'calendar did not render');
  const count=Number(d.querySelector('#statTotal').textContent);
  assert(count>0,'job count is not populated: '+count);
  assert(d.querySelector('#syncState').textContent.trim(),'status not rendered');
  d.querySelector('#listView').click();
  const defaultVisible=d.querySelectorAll('#jobList .job-item').length;
  d.querySelector('#clearFilters').click();
  const allVisible=d.querySelectorAll('#jobList .job-item').length;
  console.log('COVERAGE_AUDIT raw='+jobs.jobs.length+' merged='+count+' default_filters='+defaultVisible+' cleared_filters='+allVisible);
  d.querySelector('#monthView').click();
  const target=d.querySelector('.day[data-date="2026-10-14"]');
  assert(target,'2026-10-14 is missing');
  target.dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true}));
  await new Promise(resolve=>setTimeout(resolve,20));
  const panel=d.querySelector('#dateQuickView');
  assert(!panel.hidden,'date quickview did not open');
  const rows=d.querySelectorAll('#quickDayEvents .quick-item');
  assert(rows.length>0,'job list did not populate for 2026-10-14');
  const before=d.querySelector('#quickDateTitle').textContent;
  d.querySelector('#quickPrev').click();
  const after=d.querySelector('#quickDateTitle').textContent;
  assert(before!==after,'previous day control failed');
  d.querySelector('#quickNext').click();
  assert(d.querySelector('#quickDateTitle').textContent===before,'next day control failed');
  d.querySelector('#quickClose').click();
  assert(panel.hidden,'close control did not close quickview');

  const inlinePrevious=d.querySelector('#selectedPrevDay');
  const inlineNext=d.querySelector('#selectedNextDay');
  assert(inlinePrevious&&inlineNext,'inline previous/next day controls missing');
  const beforeInline=d.querySelector('#selectedDateTitle').textContent;
  assert(beforeInline.includes('2026.10.14'),'unexpected initial inline date '+beforeInline);
  inlinePrevious.click();
  assert(d.querySelector('#selectedDateTitle').textContent.includes('2026.10.13'),'inline previous day failed');
  inlineNext.click();
  assert(d.querySelector('#selectedDateTitle').textContent===beforeInline,'inline next day failed');
  assert(panel.hidden,'inline navigation should not open popup');
  // Navigate through the first day of the month to ensure month and day list stay in sync.
  d.querySelector('.day[data-date="2026-10-01"]').click();
  d.querySelector('#quickClose').click();
  inlinePrevious.click();
  assert(d.querySelector('#monthTitle').textContent.includes('9월'),'previous across month did not update calendar');
  assert(d.querySelector('#selectedDateTitle').textContent.includes('2026.09.30'),'previous across month did not update selected date');
  inlineNext.click();
  assert(d.querySelector('#monthTitle').textContent.includes('10월'),'next across month did not update calendar');
  assert(d.querySelector('#selectedDateTitle').textContent.includes('2026.10.01'),'next across month did not update selected date');

  assert(!runtimeErrors.length,'runtime exceptions: '+runtimeErrors.join(' | '));
  console.log('PASS site boot, job count '+count+', calendar, quick day list '+rows.length+', quick prev/next, inline prev/next including month boundaries, close and runtime exception check');
  dom.window.close();
}
main().catch(e=>{console.error(e.stack||String(e));process.exit(1)});
