import*as Wd from"@hermes/plugin-sdk";import{host as rv,PALETTE_AREA as av,ROUTES_AREA as ov,SIDEBAR_NAV_AREA as lv,STATUSBAR_AREAS as cv}from"@hermes/plugin-sdk";import{host as bf}from"@hermes/plugin-sdk";import{queryClient as lf,useQuery as lh}from"@hermes/plugin-sdk";import{useEffect as cf,useState as hf}from"react";var nt=n=>n&&typeof n=="object"&&!Array.isArray(n)?n:{},qt=n=>Array.isArray(n)?n:[],Ee=(n,e="")=>typeof n=="string"?n:typeof n=="number"?String(n):e,gt=n=>typeof n=="number"&&Number.isFinite(n)?n:null,Rt=(n,e=0)=>gt(n)??e,un=(n,e=!1)=>typeof n=="boolean"?n:e,Ur=n=>typeof n=="boolean"?n:null,Rs=n=>typeof n=="string"&&n?n:null,Kd=["idle","printing","paused","finished","failed","offline"],jd=["start","clear","resume"],Qd=["ok","warn","missing","error"],ef=["pushed","on_plate","taken_off","unknown"],tf=["sent","pending","failed","no_target","dry_run"];function Lr(n){let e=nt(n);return{name:Ee(e.name),group:Ee(e.group)}}function Wo(n){if(!n||typeof n!="object")return null;let e=nt(n),t=Rs(e.stl),i=Rs(e.preview);return t||i?{stl:t,preview:i}:null}function nf(n){let e=nt(n);return{print_time_min:gt(e.print_time_min),grams:gt(e.grams),material:Ee(e.material),color:Ee(e.color),slot:gt(e.slot),slot_label:Ee(e.slot_label),eject_planned:Ur(e.eject_planned),eject_reason:Ee(e.eject_reason)}}function sf(n){let e=nt(n);return{id:Ee(e.id),label:Ee(e.label),ok:un(e.ok),detail:Ee(e.detail)}}function zc(n){let e=nt(n),t=nt(e.printer),s={state:Kd.includes(t.state)?t.state:"offline",job_name:Ee(t.job_name),progress:Rt(t.progress),remaining_min:gt(t.remaining_min),layer:gt(t.layer),total_layers:gt(t.total_layers),bed_temp:gt(t.bed_temp),errors:qt(t.errors).map(u=>({code:Ee(nt(u).code),text:Ee(nt(u).text)})).filter(u=>u.code||u.text),awaiting_plate_clear:un(t.awaiting_plate_clear)},r=e.now&&typeof e.now=="object"?nt(e.now):null,a=nt(e.camera),o=nt(e.notices),c=nt(e.watcher),l=nt(e.viewer);return{schema:Rt(e.schema,1),generated_ts:Rt(e.generated_ts),backend:Ee(e.backend),persona:Ee(e.persona),simulated:un(e.simulated),printer:s,now:r?{queue_item_id:gt(r.queue_item_id),name:Ee(r.name),for:Lr(r.for),eject_planned:Ur(r.eject_planned),model:Wo(r.model)}:null,camera:{available:un(a.available),frame:Rs(a.frame),taken_ts:gt(a.taken_ts),note:Ee(a.note)},waiting:qt(e.waiting).map(u=>{let h=nt(u),d=jd.includes(h.action)?h.action:"start";return{id:Rt(h.id),action:d,queue_item_id:gt(h.queue_item_id),name:Ee(h.name),asked_by:Lr(h.asked_by),asked_ts:gt(h.asked_ts),facts:nf(h.facts),checklist:qt(h.checklist).map(sf),request_text:Ee(h.request_text),ready:Ur(h.ready),command:Ee(h.command),alt:h.alt&&typeof h.alt=="object"&&Ee(nt(h.alt).command)?{command:Ee(nt(h.alt).command),label:Ee(nt(h.alt).label)||"Other way"}:null,model:Wo(h.model)}}),queue:qt(e.queue).map(u=>{let h=nt(u);return{id:Rt(h.id),name:Ee(h.name),for:Lr(h.for),status:Ee(h.status),ours:un(h.ours,!0),print_time_min:gt(h.print_time_min),eject_planned:Ur(h.eject_planned),model:Wo(h.model)}}),done_box:qt(e.done_box).map(u=>{let h=nt(u),d=ef.includes(h.outcome)?h.outcome:"unknown",f=Rt(h.id);return{id:f,job_id:gt(h.job_id),name:Ee(h.name),for:Lr(h.for),finished_ts:gt(h.finished_ts),outcome:d,photo:Rs(h.photo),collected:un(h.collected),collected_by:Ee(h.collected_by),detail:Ee(h.detail),command:Ee(h.command)||`home3d collected ${f}`}}),notices:{pending:Rt(o.pending),sent:Rt(o.sent),failed:Rt(o.failed),no_target:Rt(o.no_target),dry_run:Rt(o.dry_run),recent:qt(o.recent).map(u=>{let h=nt(u),d=tf.includes(h.status)?h.status:"pending";return{ts:gt(h.ts),to:Ee(h.to),group:Ee(h.group),kind:Ee(h.kind),job:Ee(h.job),status:d,attempts:Rt(h.attempts),error:Ee(h.error),text:Ee(h.text)}})},filament:{slots:qt(nt(e.filament).slots).map(u=>{let h=nt(u);return{slot:Rt(h.slot),label:Ee(h.label)||`Slot ${Rt(h.slot)}`,material:Ee(h.material),color:Ee(h.color),name:Ee(h.name),remain_pct:gt(h.remain_pct),loaded:un(h.loaded,!0)}})},needs_human:qt(e.needs_human).map(u=>{let h=nt(u);return{id:Rt(h.id),kind:Ee(h.kind),text:Ee(h.text),ts:gt(h.ts),open:un(h.open,!0),job:Ee(h.job),who:Ee(h.who),resolved_by:Ee(h.resolved_by)}}),upgrades:qt(e.upgrades).map(u=>{let h=nt(u),d=Ee(h.model_ref);return{id:Ee(h.id),title:Ee(h.title),why:Ee(h.why),count:Rt(h.count),status:Ee(h.status),model_ref:/^https:\/\//.test(d)?d:""}}),designs:qt(e.designs).map(u=>{let h=nt(u);return{slug:Ee(h.slug),title:Ee(h.title)||Ee(h.slug),versions:qt(h.versions).map(d=>{let f=nt(d);return{version:Rt(f.version),stl:Rs(f.stl),previews:qt(f.previews).filter(g=>typeof g=="string"&&!!g),facts:nt(f.facts),note:Ee(f.note)}}).sort((d,f)=>d.version-f.version)}}),setup:{checked_ts:gt(nt(e.setup).checked_ts),pending:un(nt(e.setup).pending),checks:qt(nt(e.setup).checks).map(u=>{let h=nt(u),d=Qd.includes(h.status)?h.status:"warn";return{id:Ee(h.id),label:Ee(h.label),status:d,detail:Ee(h.detail),fix:Ee(h.fix)}})},watcher:{fresh:un(c.fresh),last_pass_ts:gt(c.last_pass_ts),interval:Ee(c.interval),model_calls:gt(c.model_calls)},groups:qt(e.groups).map(u=>({name:Ee(nt(u).name),tone:Ee(nt(u).tone,"family"),language:Ee(nt(u).language),members:Rt(nt(u).members)})).filter(u=>u.name),viewer:{is_owner:un(l.is_owner,!0),reason:Ee(l.reason)}}}function Wi(n){let e=n?.name?.trim()||"",t=n?.group?.trim()||"";return e?t?`${e} (${t})`:e:t?`someone (${t})`:"someone"}function bn(n){if(n==null||!Number.isFinite(n)||n<0)return"";let e=Math.round(n);if(e<1)return"under a minute";if(e<60)return`${e} min`;let t=Math.floor(e/60),i=e%60;return i?`${t} h ${String(i).padStart(2,"0")} min`:`${t} h`}function rf(n){return n==null||!Number.isFinite(n)||n<=0?null:n>1e12?n/1e3:n}function Kt(n,e){let t=rf(n);if(t===null)return"";let i=Math.max(0,e-t);if(i<5)return"just now";if(i<60)return`${Math.floor(i)} s ago`;if(i<3600)return`${Math.floor(i/60)} min ago`;if(i<86400)return`${Math.floor(i/3600)} h ago`;let s=Math.floor(i/86400);return s===1?"yesterday":`${s} days ago`}function Vc(n){return{idle:"Idle",printing:"Printing",paused:"Paused",finished:"Finished",failed:"Failed",offline:"Offline"}[n]}function Hc(n){return{idle:"neutral",printing:"accent",paused:"warn",finished:"good",failed:"bad",offline:"bad"}[n]}function Ps(n){let e=Number.isFinite(n.progress)?n.progress:0;return Math.max(0,Math.min(100,Math.round(e)))}var Fr=n=>n==="printing"||n==="paused";function Xo(n){return n.waiting.length?Fr(n.printer.state)?n.waiting.some(e=>e.action!=="start"||$o(e)):!0:!1}function Gc(n){return Xo(n)?[]:n.waiting}function Wc(n){return Xo(n)?"approve":Fr(n.printer.state)?"running":n.printer.state==="offline"?"offline":n.printer.state==="failed"||n.printer.errors.length||n.printer.awaiting_plate_clear?"attention":"idle"}function Xc(n){let e=n.printer,t=n.now?.for?.name?.trim();if(Xo(n))return{text:`Waiting for you: ${n.waiting.length}`,tone:"accent"};if(e.state==="printing"){let i=[`Printing ${Ps(e)}%${t?` for ${t}`:""}`],s=bn(e.remaining_min);return s&&i.push(`${s} left`),n.waiting.length&&i.push(`${n.waiting.length} waiting`),{text:i.join(", "),tone:"neutral"}}return e.state==="paused"?{text:`Paused ${Ps(e)}%${t?` for ${t}`:""}`,tone:"warn"}:e.state==="failed"?{text:"Print failed",tone:"bad"}:e.state==="offline"?{text:"Printer offline",tone:"bad"}:e.awaiting_plate_clear?{text:"Plate needs clearing",tone:"warn"}:e.state==="finished"?{text:t?`Finished for ${t}`:"Finished",tone:"good"}:{text:"Idle",tone:"neutral"}}function qc(n){if(n.action==="clear")return{button:"Plate is clear, continue",explain:"Tells the printer the bed is empty so the next job in the queue can start."};if(n.action==="resume")return{button:"Resume print",explain:"Continues the paused print from the layer where it stopped."};let e=n.facts.eject_planned===!0?"When it is done the printer pushes it off into the done box.":n.facts.eject_planned===!1?"It stays on the plate until someone takes it off.":"";return{button:"Start print",explain:`Starts "${n.name||"this job"}" on the printer now. ${e}`.trim()}}function Yc(n){let e=n.command.trim().replace(/^\/+/,"");return e||(n.action==="start"?n.queue_item_id!==null?`home3d approve start ${n.queue_item_id}`:"":`home3d approve ${n.action}`)}var Ns=n=>n.filter(e=>!e.ok);function qo(n){return n===!0?"Pushed off into the done box":n===!1?"Stays on the plate":"Not decided"}function $c(n){return n.collected?{text:n.collected_by?`Collected by ${n.collected_by}`:"Collected",tone:"neutral"}:n.outcome==="pushed"?{text:"In the done box",tone:"good"}:n.outcome==="taken_off"?{text:"Taken off the plate",tone:"good"}:n.outcome==="on_plate"?{text:"Still on the plate",tone:"warn"}:{text:"Finished",tone:"neutral"}}function Is(n){let e=(n||"").trim().replace(/^#/,"");return/^[0-9a-f]{3}$/i.test(e)?`#${e.split("").map(t=>t+t).join("")}`.toLowerCase():/^[0-9a-f]{6}([0-9a-f]{2})?$/i.test(e)?`#${e.slice(0,6)}`.toLowerCase():null}function Ds(n,e){return e===null?null:n.find(t=>t.slot===e)??null}function Zc(n,e){return Is(n?.color)??Is(Ds(e,n?.slot??null)?.color)??null}function Jc(n,e){let t=Ds(e,n.slot);return{material:n.material||t?.material||"",name:t?.name||(Is(n.color)?"":n.color),where:n.slot_label||t?.label||(n.slot!==null?`Slot ${n.slot}`:"")}}function Yo(n){let e=(n||"").trim();return e?e.charAt(0).toLocaleUpperCase()+e.slice(1):""}function Kc(n){let e=Array.from((n||"").trim())[0];return e?e.toLocaleUpperCase():"?"}function jc(n,e){return n.slot_label||Ds(e,n.slot)?.label||(n.slot!==null?`Slot ${n.slot}`:"its slot")}function $o(n){return n.ready??n.checklist.every(e=>e.ok)}var af={started:"Print started",finished:"Print finished",finished_ejected:"Finished and pushed off",failed:"Print failed",stopped:"Print stopped",paused:"Print paused",approval_request:"Asked you to approve",plate_clear:"Plate is clear",plate_not_clear:"Plate is not clear",ready_next:"Ready for the next job",delivery_failed:"Some messages were not delivered"};function Qc(n){let e=n.text.replace(/^[^\p{L}\p{N}"“]+/u,"").trim();if(e)return e.length>90?`${e.slice(0,88).trimEnd()}\u2026`:e;let i=n.kind.split(",").filter(Boolean).map(r=>af[r]??r.replace(/_/g," ")).join(", "),s=i?i[0].toUpperCase()+i.slice(1):"Message";return n.job?`${s}: ${n.job}`:s}function eh(n){if(n.failed)return{text:`${n.failed} not delivered${n.pending?`, ${n.pending} waiting to send`:""}`,tone:"bad"};if(n.pending)return{text:`${n.pending} waiting to send`,tone:"warn"};let e=n.recent.filter(t=>t.status==="no_target").length;return e?{text:`${e} of the last ${n.recent.length} had no chat to go to`,tone:"warn"}:n.recent.length&&n.recent.every(t=>t.status==="dry_run")?{text:"Simulated: messages are written, not sent",tone:"neutral"}:{text:n.recent.length?"Everyone was told":"Nothing to tell yet",tone:n.recent.length?"good":"neutral"}}function th(n){return{sent:"Sent",pending:"Waiting",failed:"Failed",no_target:"No chat to send to",dry_run:"Simulated, not sent"}[n]}function nh(n){return n==="sent"?"good":n==="failed"?"bad":n==="dry_run"?"neutral":"warn"}function ih(n){if(!n.length)return{text:"No checks reported",tone:"neutral"};let e=n.filter(s=>s.status==="error"||s.status==="missing").length,t=n.filter(s=>s.status==="warn").length,i=n.length-e-t;return e?{text:`${e} need fixing, ${i} of ${n.length} fine`,tone:"bad"}:t?{text:`${t} to look at, ${i} of ${n.length} fine`,tone:"warn"}:{text:`All ${n.length} checks pass`,tone:"good"}}function sh(n){let e={error:0,missing:1,warn:2,ok:3};return n.map((t,i)=>({c:t,i})).sort((t,i)=>e[t.c.status]-e[i.c.status]||t.i-i.i).map(t=>t.c)}function rh(n,e){let t=Kt(n.last_pass_ts,e),i=n.interval?` (every ${n.interval})`:"";return t?{text:`Watcher ${n.fresh?"checked":"last checked"} ${t}${i}`,tone:n.fresh?"good":"warn"}:{text:"Watcher has not run yet",tone:"warn"}}function Ls(n,e){let t=n.find(i=>i.name.toLowerCase()===e.trim().toLowerCase())?.tone;return t==="family"||t==="team"?t:"other"}function ah(n){let e=[],t=Array.isArray(n.size_mm)?n.size_mm.filter(a=>typeof a=="number"):[];t.length===3&&e.push(`${t.map(a=>(Math.round(a*10)/10).toString()).join(" \xD7 ")} mm`);let i=gt(n.est_grams_max)??gt(n.grams);i!==null&&e.push(`about ${Math.round(i)} g`);let s=gt(n.print_time_min);s!==null&&e.push(bn(s));let r=gt(n.volume_cm3);return r!==null&&i===null&&e.push(`${Math.round(r*10)/10} cm\xB3`),n.fits_build_volume===!1&&e.push("too big for the bed"),e}function Us(n){let e=n instanceof Error?n.message:typeof n=="string"?n:String(n??""),t=/^\s*(\d{3})\b/.exec(e),i=t?Number(t[1]):null,r=/"detail"\s*:\s*"([^"]+)"/.exec(e)?.[1]||e||"No answer";return i===404?{kind:"not_enabled",status:i,text:r}:i===null||i>=500||/fetch|network|timed? ?out|ECONN|abort/i.test(e)?{kind:"unreachable",status:i,text:r}:{kind:"error",status:i,text:r}}var of=15e3;function oh(n,e,t){if(!n)return{stale:t,text:t?"No data yet":"",ago:""};let i=Math.max(0,e-n),s=Kt(n/1e3,e/1e3),r=t||i>of;return{stale:r,text:r?`Last update ${s}`:`Updated ${s}`,ago:s}}var ch=["home-3d-workshop","overview"],uf=5e3;function Xi(n,e=uf){let t=lh({queryKey:ch,queryFn:async()=>zc(await n("overview",{timeoutMs:2e4})),refetchInterval:e,retry:1});return{ov:t.data??null,error:t.error,failing:t.isError,loading:t.isPending&&!t.data,updatedAt:t.dataUpdatedAt||0,refetch:()=>{t.refetch()}}}function Fs(){lf.invalidateQueries({queryKey:ch})}function Or(n,e,t=!0){let i=lh({queryKey:["home-3d-workshop","file",e??""],queryFn:()=>n(`file?ref=${encodeURIComponent(e??"")}`,{timeoutMs:6e4}),enabled:t&&!!e,staleTime:1/0,gcTime:6e5,retry:1});return{file:i.data??null,error:i.isError?i.error:null,loading:!!e&&t&&i.isPending}}function hh(n=1e3){let[e,t]=hf(()=>Date.now());return cf(()=>{let i=setInterval(()=>t(Date.now()),n);return()=>clearInterval(i)},[n]),e}import{Fragment as zt,jsx as Ye,jsxs as Vt}from"react/jsx-runtime";var uh={play:Ye("path",{d:"M5 3.5v9l7-4.5z",fill:"currentColor",stroke:"none"}),pause:Vt(zt,{children:[Ye("rect",{x:"4",y:"3.5",width:"2.6",height:"9",rx:".6",fill:"currentColor",stroke:"none"}),Ye("rect",{x:"9.4",y:"3.5",width:"2.6",height:"9",rx:".6",fill:"currentColor",stroke:"none"})]}),stop:Ye("rect",{x:"4",y:"4",width:"8",height:"8",rx:"1.2",fill:"currentColor",stroke:"none"}),check:Ye("path",{d:"M3.5 8.5l3 3 6-7"}),x:Ye("path",{d:"M4.5 4.5l7 7m0-7l-7 7"}),alert:Vt(zt,{children:[Ye("path",{d:"M8 2.5l6 11H2z"}),Ye("path",{d:"M8 7v3m0 1.8v.2"})]}),dot:Ye("circle",{cx:"8",cy:"8",r:"3",fill:"currentColor",stroke:"none"}),ring:Ye("circle",{cx:"8",cy:"8",r:"3.2"}),clock:Vt(zt,{children:[Ye("circle",{cx:"8",cy:"8",r:"5.5"}),Ye("path",{d:"M8 5v3.2l2 1.3"})]}),cube:Vt(zt,{children:[Ye("path",{d:"M8 2l5.5 3v6L8 14l-5.5-3V5z"}),Ye("path",{d:"M2.5 5L8 8l5.5-3M8 8v6"})]}),camera:Vt(zt,{children:[Ye("rect",{x:"2",y:"4.5",width:"12",height:"8.5",rx:"1.5"}),Ye("path",{d:"M5.5 4.5l1-2h3l1 2"}),Ye("circle",{cx:"8",cy:"8.7",r:"2.3"})]}),refresh:Vt(zt,{children:[Ye("path",{d:"M13 8a5 5 0 1 1-1.5-3.6"}),Ye("path",{d:"M13 2.5v3h-3"})]}),box:Vt(zt,{children:[Ye("path",{d:"M2.5 6h11v7.5h-11z"}),Ye("path",{d:"M1.8 3.5h12.4V6H1.8zM6.5 8.5h3"})]}),spool:Vt(zt,{children:[Ye("circle",{cx:"8",cy:"8",r:"5.5"}),Ye("circle",{cx:"8",cy:"8",r:"1.6"})]}),bell:Vt(zt,{children:[Ye("path",{d:"M4 11V7.5a4 4 0 0 1 8 0V11l1 1.2H3z"}),Ye("path",{d:"M6.6 13.8a1.5 1.5 0 0 0 2.8 0"})]}),hand:Vt(zt,{children:[Ye("path",{d:"M5 8V3.8a1 1 0 0 1 2 0V7.5m0-4.7a1 1 0 0 1 2 0v4.7m0-3.7a1 1 0 0 1 2 0V9"}),Ye("path",{d:"M11 6.5a1 1 0 0 1 2 0V10a4.5 4.5 0 0 1-4.5 4.5h-.7A4 4 0 0 1 4.6 13L2.8 10a1 1 0 0 1 1.6-1.2L5 9.6"})]}),spark:Ye("path",{d:"M8 2v3m0 6v3M2 8h3m6 0h3M4 4l2 2m4 4l2 2m0-8l-2 2M6 10l-2 2"}),layers:Vt(zt,{children:[Ye("path",{d:"M8 2.5l6 3-6 3-6-3z"}),Ye("path",{d:"M2 8.5l6 3 6-3M2 11.2l6 3 6-3"})]}),thermo:Ye(zt,{children:Ye("path",{d:"M6.5 9.5V3.5a1.5 1.5 0 0 1 3 0v6a2.8 2.8 0 1 1-3 0z"})}),arrow:Ye("path",{d:"M3 8h9m-3.5-3.5L12 8l-3.5 3.5"}),link:Ye("path",{d:"M6.5 9.5l3-3M7 4.5l1-1a2.5 2.5 0 0 1 3.5 3.5l-1 1M9 11.5l-1 1A2.5 2.5 0 0 1 4.5 9l1-1"}),copy:Vt(zt,{children:[Ye("rect",{x:"5.5",y:"5.5",width:"8",height:"8",rx:"1.3"}),Ye("path",{d:"M10.5 3.5v-.3a1 1 0 0 0-1-1h-6a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h.3"})]}),wrench:Ye("path",{d:"M10.2 2.4a3.3 3.3 0 0 0-3.7 4.4L2.7 10.6a1.4 1.4 0 0 0 2 2l3.8-3.8a3.3 3.3 0 0 0 4.4-3.7l-2 2-2-.6-.6-2z"}),eject:Vt(zt,{children:[Ye("path",{d:"M3 9.5L8 4l5 5.5z"}),Ye("path",{d:"M3 12.5h10"})]}),reset:Vt(zt,{children:[Ye("path",{d:"M3.5 8a4.5 4.5 0 1 0 1.4-3.2"}),Ye("path",{d:"M3 2.8v2.6h2.6"})]})};function Ie({name:n,size:e=14,title:t}){return Vt("svg",{"aria-hidden":t?void 0:!0,role:t?"img":void 0,width:e,height:e,viewBox:"0 0 16 16",fill:"none",stroke:"currentColor",strokeWidth:1.4,strokeLinecap:"round",strokeLinejoin:"round",style:{flexShrink:0},children:[t?Ye("title",{children:t}):null,uh[n]??uh.dot]})}import{host as mh}from"@hermes/plugin-sdk";import{useCallback as xf,useRef as vf,useState as Jo}from"react";function df(n){let e=n.trim();if(/[\n\r\t;&|`$<>]/.test(e))throw new Error(`not a workshop command: ${n}`);let t=e.replace(/^\/+/,"").replace(/ +/g," ");if(!/^home3d( |$)/.test(t))throw new Error(`not a workshop command: ${n}`);return t}var ff=/(?:^|\n)[ \t]*\[home3d:(ok|not_done)(?::([a-z0-9_]+))?\][ \t]*$/;function pf(n){let e=ff.exec(n);if(!e)return{ok:!mf(n),code:"",text:n.trim(),marked:!1};let t=e[1]==="ok";return{ok:t,code:t?"ok":e[2]||"not_done",text:n.slice(0,e.index).trim(),marked:!0}}function mf(n){return/^\s*(?:\S+\s+)?(not done|refused|cannot|can't|error|failed|no such|unknown|only the owner|nothing is printing|usage)/i.test(n)}var Zo=n=>n instanceof Error?n.message:String(n??"unknown error");function dh(n){let e=[n?.output,n?.warning].filter(i=>typeof i=="string"&&i.trim()).join(`
`).trim();if(!e)return{kind:"ran",ok:!0,text:"Done. The command sent no reply."};let t=pf(e);return{kind:"ran",ok:t.ok,text:t.text||(t.ok?"Done.":"Not done.")}}var gf="Workshop actions (home-3d-workshop)",qi=null;async function _f(n){if(qi)return qi;try{let e=await n.request("session.create",{title:gf,hidden:!0});qi=typeof e?.session_id=="string"&&e.session_id?e.session_id:null}catch{qi=null}return qi}async function fh(n,e){let t;try{t=df(e)}catch(r){return{kind:"failed",ok:!1,text:Zo(r)}}let i=null;try{i=n.state?.focusedSessionId?.get()??null}catch{i=null}if(i)try{return dh(await n.request("slash.exec",{session_id:i,command:t}))}catch(r){return{kind:"failed",ok:!1,text:`The command did not run: ${Zo(r)}`}}let s=await _f(n);if(s)try{return dh(await n.request("slash.exec",{session_id:s,command:t}))}catch(r){if(qi=null,!n.composer?.insertText)return{kind:"failed",ok:!1,text:`The command did not run: ${Zo(r)}`}}try{if(await n.composer?.insertText?.(null,`/${t}`,{mode:"prefix"}))return{kind:"seated",ok:!0,text:`No chat is open here, so /${t} is waiting in the message box. Press Enter there to send it.`}}catch{}return{kind:"manual",ok:!1,text:`No chat is open here. Open a chat with the printer and send /${t}`}}var ph=`
.h3w {
  --w-fg: var(--ui-text-primary, CanvasText);
  --w-fg2: var(--ui-text-secondary, color-mix(in srgb, CanvasText 72%, transparent));
  --w-fg3: var(--ui-text-tertiary, color-mix(in srgb, CanvasText 52%, transparent));
  --w-line: var(--ui-stroke-secondary, color-mix(in srgb, CanvasText 11%, transparent));
  --w-line2: var(--ui-stroke-primary, color-mix(in srgb, CanvasText 18%, transparent));
  --w-card: var(--ui-bg-card, color-mix(in srgb, CanvasText 3%, transparent));
  --w-raise: var(--ui-bg-elevated, Canvas);
  --w-well: color-mix(in srgb, var(--w-fg) 4%, transparent);
  --w-hover: var(--ui-control-hover-background, color-mix(in srgb, CanvasText 6%, transparent));
  --w-accent: var(--ui-accent, #4f7cff);
  --w-on-accent: var(--ui-accent-foreground, #fff);
  --w-red: var(--ui-red, #d1435b);
  --w-green: var(--ui-green, #2f9a72);
  --w-orange: var(--ui-orange, #db704b);
  --w-yellow: var(--ui-yellow, #c08532);
  --w-blue: var(--ui-blue, #3a6df0);
  /* the workshop's own: the textured build sheet, the heatbed under it, the studio around them */
  --w-plate: #75695a;
  --w-bed: #26272b;
  --w-studio: radial-gradient(95% 85% at 50% 30%, #3b3c41, #17181a);
  --w-on-photo: #fff;
  /* small grey text that still reads at 12 px; --w-fg3 stays for icons and rules */
  --w-quiet: color-mix(in srgb, var(--w-fg) 68%, transparent);
  color: var(--w-fg);
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
/* Text on the accent: white on a dark accent, a dark tint of it on a light one (dark themes use a light accent). */
@supports (color: oklch(from red l c h)) {
  .h3w { --w-on-accent: var(--ui-accent-foreground, oklch(from var(--w-accent) clamp(0.17, (0.58 - l) * 999, 1) calc(c * 0.35) h)); }
}
.h3w *, .h3w *::before, .h3w *::after { box-sizing: border-box; }
.h3w button { font: inherit; color: inherit; }
.h3w :focus-visible { outline: 2px solid var(--w-accent); outline-offset: 2px; border-radius: 6px; }
.h3w h1, .h3w h2, .h3w h3, .h3w p, .h3w blockquote, .h3w dl, .h3w dd { margin: 0; }
.h3w .num { font-variant-numeric: tabular-nums; }
.h3w .muted { color: var(--w-fg2); }
.h3w .faint { color: var(--w-quiet); }
.h3w .ellipsis { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }

/* tones */
.h3w .t-neutral { --tone: var(--w-fg2); }
.h3w .t-accent { --tone: var(--w-accent); }
.h3w .t-good { --tone: var(--w-green); }
.h3w .t-warn { --tone: var(--w-yellow); }
.h3w .t-bad { --tone: var(--w-red); }
/* A tone as text: mixed toward the text colour so small coloured words stay readable in both themes. */
.h3w .t-neutral, .h3w .t-accent, .h3w .t-good, .h3w .t-warn, .h3w .t-bad { --ink: color-mix(in srgb, var(--tone) 64%, var(--w-fg)); }
.h3w .w-ink { color: var(--ink); font-weight: 600; }
/* the group a person asked from */
.h3w .g-family { --g: var(--w-orange); }
.h3w .g-team { --g: var(--w-blue); }
.h3w .g-other { --g: var(--w-fg3); }

/* page frame */
.h3w-scroll { height: 100%; overflow: auto; }
.h3w.w-page { container: h3w / inline-size; max-width: 1280px; margin: 0 auto; padding: 26px 32px 64px; }
@container h3w (max-width: 620px) {
  .h3w.w-page { padding-left: 16px; padding-right: 16px; }
  .h3w .w-strip-job { flex: 1 1 100%; flex-wrap: wrap; order: 3; }
  .h3w .w-spec { grid-template-columns: minmax(0, 1fr); gap: 1px; }
  .h3w .w-spec dd { margin-bottom: 7px; }
}
.h3w .w-top { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
.h3w .w-title { font-size: 22px; font-weight: 700; letter-spacing: -0.015em; line-height: 1.2; }
.h3w .w-sub { color: var(--w-fg2); margin-top: 4px; font-size: 13px; max-width: 64ch; }
.h3w .w-top-right { margin-left: auto; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.h3w .w-fresh { display: inline-flex; align-items: center; gap: 7px; color: var(--w-quiet); font-size: 12px; }
.h3w .w-fresh.stale { color: color-mix(in srgb, var(--w-yellow) 64%, var(--w-fg)); }
.h3w .w-pulse { width: 6px; height: 6px; border-radius: 50%; background: var(--w-green); }
.h3w .w-fresh.stale .w-pulse { background: var(--w-yellow); }

.h3w .w-banner { display: flex; align-items: flex-start; gap: 10px; padding: 10px 13px; border-radius: 9px; margin-bottom: 12px;
  border: 1px solid color-mix(in srgb, var(--tone) 30%, transparent); background: color-mix(in srgb, var(--tone) 7%, transparent); color: var(--w-fg); }
.h3w .w-banner > svg { color: var(--tone); margin-top: 3px; }
.h3w .w-banner > span { min-width: 0; overflow-wrap: anywhere; }
.h3w .w-sim { display: inline-flex; align-items: center; gap: 6px; padding: 2px 9px 2px 7px; border-radius: 6px; font-size: 12px; font-weight: 600;
  color: color-mix(in srgb, var(--w-orange) 64%, var(--w-fg)); border: 1px dashed color-mix(in srgb, var(--w-orange) 60%, transparent); }

/* buttons */
.h3w .w-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; height: 30px; padding: 0 12px; border-radius: 9px;
  border: 1px solid var(--w-line2); background: transparent; font-weight: 600; font-size: 13px; cursor: pointer; white-space: nowrap; transition: background .12s, border-color .12s; }
.h3w .w-btn:hover:not(:disabled) { background: var(--w-hover); }
.h3w .w-btn:disabled { opacity: .5; cursor: not-allowed; }
.h3w .w-btn.ghost { border-color: transparent; color: var(--w-fg2); }
.h3w .w-btn.ghost:hover:not(:disabled) { color: var(--w-fg); }
.h3w .w-btn.sm { height: 27px; padding: 0 9px; font-size: 12px; border-radius: 9px; }
.h3w .w-btn.primary { height: 44px; padding: 0 22px 0 18px; gap: 9px; font-size: 15px; font-weight: 700; letter-spacing: -0.005em; border: 0; border-radius: 12px;
  background: var(--w-accent); color: var(--w-on-accent);
  box-shadow: 0 1px 1px color-mix(in srgb, #000 14%, transparent), 0 6px 16px -6px color-mix(in srgb, var(--w-accent) 70%, transparent), inset 0 1px 0 color-mix(in srgb, #fff 22%, transparent);
  transition: background .12s, transform .06s; }
.h3w .w-btn.primary:hover:not(:disabled) { background: color-mix(in srgb, var(--w-accent) 90%, var(--w-fg)); }
.h3w .w-btn.primary:active:not(:disabled) { transform: translateY(1px); }
.h3w .w-btn.primary.muted-primary { background: transparent; color: var(--w-accent); border: 1px solid color-mix(in srgb, var(--w-accent) 55%, transparent); box-shadow: none; }
.h3w .w-btn.danger { color: color-mix(in srgb, var(--w-red) 70%, var(--w-fg)); border-color: color-mix(in srgb, var(--w-red) 40%, transparent); }
.h3w .w-btn.danger:hover:not(:disabled) { background: color-mix(in srgb, var(--w-red) 9%, transparent); }
.h3w .w-btn.danger-solid { color: #fff; background: var(--w-red); border-color: var(--w-red); }
.h3w .w-btn.danger-solid:hover:not(:disabled) { background: color-mix(in srgb, var(--w-red) 88%, #000); }
.h3w .w-link { border: 0; background: none; padding: 0; color: var(--w-accent); cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; }
.h3w .w-link:hover { text-decoration: underline; }

/* tags, people */
.h3w .w-tag { display: inline-flex; align-items: center; gap: 4px; padding: 1px 7px; border-radius: 6px; font-size: 12px; font-weight: 600; white-space: nowrap; line-height: 1.5;
  color: var(--ink, var(--tone)); background: color-mix(in srgb, var(--tone) 10%, transparent); }
.h3w .w-tag.outline { background: transparent; box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--tone) 38%, transparent); }
.h3w .w-person { display: inline-flex; align-items: baseline; gap: 6px; white-space: nowrap; min-width: 0; max-width: 100%; vertical-align: bottom; }
.h3w .w-person b { font-weight: 600; color: var(--w-fg); overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.h3w .w-person .grp { color: var(--w-fg2); display: inline-flex; align-items: center; gap: 4px; min-width: 0; flex-shrink: 2; }
.h3w .w-person .grp > span { overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.h3w .w-person .grp::before { flex-shrink: 0; }
.h3w .w-for { display: inline-flex; align-items: baseline; gap: 5px; min-width: 0; flex-shrink: 4; }
.h3w .w-person .grp::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--g, var(--w-fg3)); transform: translateY(-1px); }
.h3w .w-ava { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700; line-height: 1; color: color-mix(in srgb, var(--g, var(--w-fg2)) 60%, var(--w-fg)); background: color-mix(in srgb, var(--g, var(--w-fg3)) 18%, transparent); }
.h3w .w-ava.sm { width: 18px; height: 18px; font-size: 10px; }

/* hero */
.h3w .w-hero { border: 1px solid var(--w-line); border-radius: 16px; background: var(--w-card); overflow: hidden; }
.h3w .w-strip { display: flex; align-items: center; gap: 12px; padding: 11px 20px; min-height: 52px; flex-wrap: wrap; }
.h3w .w-strip + .w-hero-body, .h3w .w-strip + .w-reply, .h3w .w-strip + .w-tabs, .h3w .w-strip + .w-idle { border-top: 1px solid var(--w-line); }
.h3w .w-state { display: inline-flex; align-items: center; gap: 8px; font-weight: 600; font-size: 13px; color: var(--ink, var(--tone)); }
.h3w .w-state .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--tone); box-shadow: 0 0 0 3px color-mix(in srgb, var(--tone) 18%, transparent); }
.h3w .w-state.live .dot { animation: h3w-breathe 2.4s ease-in-out infinite; }
@keyframes h3w-breathe { 50% { box-shadow: 0 0 0 6px color-mix(in srgb, var(--tone) 6%, transparent); } }
@media (prefers-reduced-motion: reduce) { .h3w .w-state.live .dot { animation: none; } }
.h3w .w-strip-job { display: flex; align-items: baseline; gap: 8px; min-width: 0; flex: 1 1 220px; }
.h3w .w-strip-job .name { font-weight: 600; flex-shrink: 1; }
.h3w .w-strip-meta { display: flex; align-items: center; gap: 14px; color: var(--w-fg2); font-size: 12px; flex-wrap: wrap; }
.h3w .w-strip-meta span { display: inline-flex; align-items: center; gap: 5px; }
.h3w .w-strip-actions { display: flex; gap: 8px; margin-left: auto; }
.h3w .w-strip-bar { height: 3px; background: color-mix(in srgb, var(--w-fg) 8%, transparent); }
.h3w .w-strip-bar > i { display: block; height: 100%; background: var(--w-accent); transition: width .6s ease; }

.h3w .w-hero-body { display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(0, 1fr); gap: 28px; padding: 20px; }
.h3w .w-hero-body.single { grid-template-columns: minmax(0, 1fr); }
@container h3w (max-width: 900px) { .h3w .w-hero-body { grid-template-columns: minmax(0, 0.9fr) minmax(0, 1fr); gap: 20px; } }
@container h3w (max-width: 680px) { .h3w .w-hero-body { grid-template-columns: minmax(0, 1fr); gap: 18px; padding: 16px; } }

.h3w .w-tabs { display: flex; align-items: center; gap: 6px; padding: 14px 20px 0; flex-wrap: wrap; }
.h3w .w-tabs-label { color: var(--w-fg2); font-size: 12px; margin-right: 6px; }
.h3w .w-tab { display: inline-flex; align-items: center; gap: 7px; border: 1px solid transparent; background: transparent; border-radius: 9px; padding: 4px 11px 4px 5px;
  font-size: 12px; cursor: pointer; color: var(--w-fg2); max-width: 260px; }
.h3w .w-tab:hover { background: var(--w-hover); }
.h3w .w-tab[aria-pressed="true"] { border-color: var(--w-line2); color: var(--w-fg); background: var(--w-raise); font-weight: 600; }

/* the request: who, their words as a chat bubble, then what was prepared */
.h3w .w-ask { min-width: 0; display: flex; flex-direction: column; }
.h3w .w-sender { display: flex; align-items: center; gap: 9px; min-width: 0; }
.h3w .w-sender > .faint { flex-shrink: 0; white-space: nowrap; }
.h3w .w-bubble { align-self: flex-start; max-width: 100%; margin-top: 9px; padding: 12px 16px 13px; border-radius: 5px 18px 18px 18px;
  font-size: 19px; line-height: 1.4; font-weight: 400; letter-spacing: -0.008em; overflow-wrap: anywhere;
  background: color-mix(in srgb, var(--g, var(--w-fg3)) 10%, var(--w-raise)); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--g, var(--w-fg3)) 24%, transparent); }
.h3w .w-bubble > .words.clamped { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 5; overflow: hidden; }
.h3w .w-bubble-more { align-self: flex-start; margin-top: 6px; font-size: 12px; }
.h3w .w-bubble.long { font-size: 15px; line-height: 1.45; }
.h3w .w-jobline { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
.h3w .w-job { font-size: 15px; font-weight: 600; min-width: 0; overflow-wrap: anywhere; }
.h3w .w-big { font-size: 22px; font-weight: 600; letter-spacing: -0.015em; line-height: 1.22; text-wrap: balance; min-width: 0; overflow-wrap: anywhere; }
.h3w .w-asked { margin-top: 6px; color: var(--w-fg2); display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: baseline; }
.h3w .w-spec { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 7px 20px; margin: 12px 0 0; }
.h3w .w-spec dt { color: var(--w-quiet); }
.h3w .w-spec dd { font-weight: 600; display: flex; align-items: center; gap: 7px; min-width: 0; flex-wrap: wrap; }
.h3w .w-spec dd .more { font-weight: 400; color: var(--w-fg2); }
.h3w .w-swatch { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; background: var(--sw, transparent); box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--w-fg) 24%, transparent); }
.h3w .w-checks-sum { display: flex; align-items: center; gap: 7px; margin-top: 18px; font-weight: 600; color: var(--ink, var(--tone)); }
.h3w .w-checks { list-style: none; margin: 8px 0 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px 20px; }
@container h3w (max-width: 1000px) { .h3w .w-checks { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-checks li { display: grid; grid-template-columns: 16px minmax(0, 1fr); gap: 7px; align-items: start; }
.h3w .w-checks li > svg { margin-top: 3px; }
.h3w .w-checks li > span { min-width: 0; overflow-wrap: anywhere; }
.h3w .w-checks .ok > svg { color: var(--w-green); }
.h3w .w-checks .no { grid-column: 1 / -1; font-weight: 600; }
.h3w .w-checks .no > svg { color: var(--w-red); }
.h3w .w-checks .detail { display: block; color: var(--w-quiet); font-size: 12px; font-weight: 400; }
.h3w .w-go { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-top: auto; padding-top: 20px; }
.h3w .w-go-explain { color: var(--w-fg2); font-size: 12px; flex: 1 1 200px; min-width: 0; overflow-wrap: anywhere; }
.h3w .w-cmd { font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 12px; color: var(--w-quiet); }

/* now printing */
.h3w .w-run { min-width: 0; align-self: center; }
.h3w .w-pct { font-size: 64px; font-weight: 700; letter-spacing: -0.04em; line-height: 1; margin-top: 20px; }
.h3w .w-pct small { font-size: 24px; font-weight: 600; letter-spacing: 0; color: var(--w-fg3); margin-left: 3px; }
.h3w .w-bigbar { height: 10px; border-radius: 6px; background: color-mix(in srgb, var(--w-fg) 9%, transparent); overflow: hidden; margin: 14px 0 16px; }
.h3w .w-bigbar > i { display: block; height: 100%; border-radius: 6px; background: var(--w-accent); transition: width .6s ease; }
.h3w .w-lines { display: grid; gap: 8px; color: var(--w-fg2); }
.h3w .w-lines > div { display: flex; gap: 9px; align-items: center; }
.h3w .w-lines > div > svg { color: var(--w-fg3); }
.h3w .w-lines b { color: var(--w-fg); font-weight: 600; }

.h3w .w-confirm { margin-top: 12px; padding: 12px 14px; border-radius: 9px; border: 1px solid color-mix(in srgb, var(--w-red) 40%, transparent);
  background: color-mix(in srgb, var(--w-red) 6%, transparent); display: grid; gap: 10px; }
.h3w .w-confirm .row { display: flex; gap: 8px; flex-wrap: wrap; }
.h3w .w-reply { display: flex; gap: 10px; align-items: flex-start; padding: 10px 20px; font-size: 12px; background: color-mix(in srgb, var(--tone) 7%, transparent); }
.h3w .w-reply > svg { color: var(--tone); margin-top: 3px; }
.h3w .w-reply pre { margin: 0; white-space: pre-wrap; font: inherit; flex: 1; min-width: 0; }
.h3w .w-reply-inline { margin-top: 8px; border-radius: 9px; padding: 8px 10px; }

.h3w .w-idle { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 320px); gap: 28px; align-items: center; padding: 22px 20px; }
@container h3w (max-width: 680px) { .h3w .w-idle { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-idle .w-big { font-size: 19px; }
.h3w .w-idle p { max-width: 62ch; }

/* media: the plate (3D), the camera, thumbnails */
.h3w .w-media { position: relative; border-radius: 12px; overflow: hidden; background: var(--w-well); border: 1px solid var(--w-line); aspect-ratio: 4 / 3; min-height: 200px; }
.h3w .w-media[data-workshop-viewer="live"], .h3w .w-media[data-workshop-camera] { background: var(--w-studio); border-color: color-mix(in srgb, #000 30%, var(--w-line)); }
.h3w .w-media.wide { aspect-ratio: 16 / 10; }
.h3w .w-media.short { aspect-ratio: auto; height: 190px; min-height: 0; }
.h3w .w-media.tall { aspect-ratio: auto; min-height: 380px; }
@container h3w (max-width: 900px) { .h3w .w-media.tall { min-height: 300px; } }
@container h3w (max-width: 680px) { .h3w .w-media.tall, .h3w .w-media.wide { aspect-ratio: 16 / 10; min-height: 0; max-height: 300px; width: 100%; } }
.h3w .w-media .stage { position: absolute; inset: 0; cursor: grab; }
.h3w .w-media .stage:active { cursor: grabbing; }
.h3w .w-media img.fill { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.h3w .w-media img.cover { object-fit: cover; }
.h3w .w-media .center { position: absolute; inset: 0; z-index: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; color: var(--w-quiet); text-align: center; padding: 16px; }
.h3w .w-media[data-workshop-viewer="live"] .center { color: color-mix(in srgb, var(--w-on-photo) 70%, transparent); }
.h3w .w-media[data-workshop-viewer="live"]::after { content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 75% 70% at 50% 46%, transparent 52%, rgba(0, 0, 0, .34)); }
.h3w .w-media .over { position: absolute; z-index: 1; display: flex; gap: 6px; align-items: center; }
.h3w .w-media .over.tl { top: 10px; left: 10px; }
.h3w .w-media .over.tr { top: 10px; right: 10px; }
.h3w .w-media .over.bl { bottom: 10px; left: 10px; }
.h3w .w-media .over.br { bottom: 10px; right: 10px; }
/* labels and controls that sit on a photo or on the plate: always light on dark glass */
.h3w .w-glass, .h3w .w-photo-cap, .h3w .w-view3d { display: inline-flex; align-items: center; gap: 6px; min-height: 26px; padding: 3px 9px; border-radius: 9px; font-size: 12px; font-weight: 600;
  color: var(--w-on-photo); background: rgba(16, 16, 18, .62); border: 1px solid rgba(255, 255, 255, .16); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); }
.h3w button.w-glass, .h3w .w-view3d { cursor: pointer; }
.h3w button.w-glass { padding: 3px 7px; }
.h3w button.w-glass:hover, .h3w .w-view3d:hover { background: rgba(16, 16, 18, .82); border-color: rgba(255, 255, 255, .32); }
.h3w .w-view3d { padding: 5px 12px; font-weight: 600; }
.h3w .w-glass:focus-visible, .h3w .w-view3d:focus-visible { outline-color: var(--w-on-photo); }
.h3w .w-media canvas:focus-visible { outline: 2px solid var(--w-on-photo); outline-offset: -5px; border-radius: 9px; }
.h3w .w-thumb { width: 48px; height: 48px; border-radius: 9px; object-fit: cover; background: var(--w-well); border: 1px solid var(--w-line); flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: var(--w-fg3); overflow: hidden; }
.h3w .w-thumb img { width: 100%; height: 100%; object-fit: cover; }
.h3w .w-skel { background: linear-gradient(90deg, var(--w-well), color-mix(in srgb, var(--w-fg) 8%, transparent), var(--w-well)); background-size: 200% 100%; animation: h3w-shimmer 1.4s linear infinite; border-radius: 9px; }
@keyframes h3w-shimmer { to { background-position: -200% 0; } }
.h3w .w-spin { animation: h3w-spin 0.9s linear infinite; }
@keyframes h3w-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .h3w .w-spin { animation: none; } }
@media (prefers-reduced-motion: reduce) { .h3w .w-skel { animation: none; } }

/* lower grid */
.h3w .w-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 36px 48px; margin-top: 34px; }
@container h3w (max-width: 900px) { .h3w .w-grid { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-col { display: grid; grid-template-columns: minmax(0, 1fr); gap: 36px; align-content: start; min-width: 0; }
.h3w .w-sec-head { display: flex; align-items: baseline; gap: 8px; padding-bottom: 9px; border-bottom: 1px solid var(--w-line2); }
.h3w .w-sec-head h2 { font-size: 15px; font-weight: 600; letter-spacing: -0.005em; display: inline-flex; align-items: baseline; gap: 8px; }
.h3w .w-sec-head .count { color: var(--w-quiet); font-weight: 400; font-size: 13px; }
.h3w .w-sec-head .aside { margin-left: auto; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.h3w .w-subhead { font-size: 13px; font-weight: 600; padding: 16px 0 2px; }
.h3w .w-empty { padding: 14px 0 4px; color: var(--w-quiet); display: flex; gap: 8px; align-items: flex-start; max-width: 62ch; }
.h3w .w-empty > svg { margin-top: 3px; }
.h3w .w-rows { list-style: none; margin: 0; padding: 0; }
.h3w .w-row { display: flex; align-items: center; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--w-line); min-width: 0; }
.h3w .w-row:last-child { border-bottom: 0; }
.h3w .w-row .w-main { flex: 1; min-width: 0; display: grid; gap: 2px; }
.h3w .w-row .title { font-weight: 600; display: flex; align-items: center; gap: 8px; min-width: 0; }
.h3w .w-row .sub { color: var(--w-fg2); font-size: 12px; display: flex; gap: 2px 12px; flex-wrap: wrap; align-items: baseline; }
.h3w .w-row .end { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.h3w .w-row .end .state { color: var(--w-quiet); font-size: 12px; }
.h3w .w-facts-line { color: var(--w-fg2); display: flex; gap: 2px 14px; flex-wrap: wrap; }
.h3w .w-facts-line .bad { color: color-mix(in srgb, var(--w-red) 70%, var(--w-fg)); font-weight: 600; }
.h3w .w-facts-line .warn { color: color-mix(in srgb, var(--w-yellow) 64%, var(--w-fg)); }
.h3w .w-row > .lead { flex-shrink: 0; margin-top: 3px; align-self: flex-start; color: var(--tone, var(--w-fg3)); }
.h3w .w-pos { width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;
  color: var(--w-fg2); box-shadow: inset 0 0 0 1px var(--w-line2); flex-shrink: 0; }
.h3w .w-row.next .w-pos { background: var(--w-accent); color: var(--w-on-accent); box-shadow: none; }

/* filament: the four spools, each wound as full as it is */
.h3w .w-slots { display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: 16px 8px; padding-top: 16px; }
.h3w .w-slot { display: grid; justify-items: center; text-align: center; min-width: 0; }
.h3w .w-slot svg { margin-bottom: 7px; overflow: visible; }
.h3w .w-slot .flange { fill: color-mix(in srgb, var(--w-fg) 12%, transparent); stroke: color-mix(in srgb, var(--w-fg) 26%, transparent); stroke-width: 1; }
.h3w .w-slot .wound { fill: var(--sw, var(--w-fg3)); stroke: color-mix(in srgb, var(--w-fg) 50%, transparent); stroke-width: 1; }
.h3w .w-slot .turn { fill: none; stroke: color-mix(in srgb, #000 13%, transparent); stroke-width: 1; }
.h3w .w-slot .hub { fill: var(--w-raise); stroke: color-mix(in srgb, var(--w-fg) 38%, transparent); stroke-width: 1; }
.h3w .w-slot .hole { fill: color-mix(in srgb, var(--w-fg) 30%, transparent); }
.h3w .w-slot.empty .flange { stroke-dasharray: 3 3; fill: none; }
.h3w .w-slot .mat { font-weight: 600; max-width: 100%; }
.h3w .w-slot .sub { font-size: 12px; color: var(--w-fg2); max-width: 100%; }
.h3w .w-slot .brand { font-size: 12px; line-height: 1.3; color: var(--w-quiet); max-width: 100%; overflow-wrap: anywhere; }
.h3w .w-slot.low .sub { color: color-mix(in srgb, var(--w-red) 70%, var(--w-fg)); font-weight: 600; }

.h3w .clamp2, .h3w .clamp3 { display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
.h3w .clamp2 { -webkit-line-clamp: 2; }
.h3w .clamp3 { -webkit-line-clamp: 3; }
.h3w .w-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--tone); flex-shrink: 0; margin-top: 7px; }
.h3w .w-camthumb { width: 60px; height: 38px; border-radius: 6px; overflow: hidden; flex-shrink: 0; border: 1px solid var(--w-line2); background: var(--w-well); padding: 0; cursor: pointer; position: relative; }
.h3w .w-camthumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.h3w .w-summary { display: flex; align-items: center; gap: 8px; padding: 12px 0 4px; font-weight: 600; }
.h3w .w-summary > svg { color: var(--tone); }
.h3w .w-watch { display: flex; align-items: center; gap: 4px 14px; flex-wrap: wrap; padding: 4px 0 8px; color: var(--w-fg2); }
.h3w .w-watch .beat { display: inline-flex; align-items: center; gap: 7px; }
.h3w .w-watch .beat::before { content: ''; width: 7px; height: 7px; border-radius: 50%; background: var(--tone); }
.h3w details.w-more summary { cursor: pointer; color: var(--w-fg2); font-size: 12px; padding: 6px 0; list-style: none; display: inline-flex; gap: 6px; align-items: center; }
.h3w details.w-more summary::-webkit-details-marker { display: none; }
.h3w details.w-more summary::before { content: '\u25B8'; font-size: 10px; transition: transform .15s; }
.h3w details.w-more[open] summary::before { transform: rotate(90deg); }
.h3w .w-fix { margin-top: 3px; font-size: 12px; color: var(--w-fg2); display: flex; gap: 6px; align-items: baseline; }
.h3w .w-fix code { font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 12px; padding: 1px 5px; border-radius: 6px; background: var(--w-well); color: var(--w-fg); }
.h3w .w-zero b { font-weight: 700; color: color-mix(in srgb, var(--w-green) 64%, var(--w-fg)); }
.h3w .w-zero.spent b { color: color-mix(in srgb, var(--w-yellow) 64%, var(--w-fg)); }

.h3w .w-design { padding: 14px 0; border-bottom: 1px solid var(--w-line); display: grid; gap: 10px; }
.h3w .w-design:last-child { border-bottom: 0; }
.h3w .w-design-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.h3w .w-vers { display: flex; gap: 4px; flex-wrap: wrap; }
.h3w .w-ver { min-width: 34px; height: 26px; padding: 0 8px; border-radius: 9px; border: 1px solid var(--w-line); background: transparent; cursor: pointer; font-size: 12px; font-weight: 600; color: var(--w-fg2); }
.h3w .w-ver:hover { border-color: var(--w-line2); color: var(--w-fg); }
.h3w .w-ver[aria-pressed="true"] { border-color: var(--w-line2); color: var(--w-fg); background: var(--w-raise); }
.h3w .w-design-body { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 16px; align-items: start; }
@container h3w (max-width: 620px) { .h3w .w-design-body { grid-template-columns: minmax(0, 1fr); } }
.h3w .w-strip-thumbs { display: flex; gap: 6px; flex-wrap: wrap; }
.h3w .w-strip-thumbs button { padding: 0; border: 1px solid var(--w-line); border-radius: 9px; background: none; cursor: pointer; overflow: hidden; width: 56px; height: 42px; }
.h3w .w-strip-thumbs button[aria-pressed="true"] { border-color: var(--w-accent); box-shadow: 0 0 0 1px var(--w-accent); }
.h3w .w-strip-thumbs img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* standalone states */
.h3w .w-state-page { max-width: 560px; margin: 8vh auto 0; text-align: left; display: grid; gap: 12px; padding: 26px; border: 1px solid var(--w-line); border-radius: 16px; background: var(--w-card); }
.h3w .w-state-page h2 { font-size: 19px; font-weight: 600; letter-spacing: -0.01em; display: flex; gap: 8px; align-items: center; }
.h3w .w-state-page ol { margin: 0; padding-left: 18px; display: grid; gap: 8px; color: var(--w-fg2); }
.h3w .w-code { display: flex; align-items: center; gap: 8px; padding: 6px 8px 6px 10px; border-radius: 9px; background: var(--w-well); border: 1px solid var(--w-line); }
.h3w .w-code code { flex: 1; font-family: var(--font-mono, ui-monospace, SFMono-Regular, Menlo, monospace); font-size: 12px; color: var(--w-fg); overflow-x: auto; white-space: nowrap; }

/* transcript card */
.h3w.w-card { border: 1px solid var(--w-line); border-radius: 16px; padding: 12px; margin: 6px 0; max-width: 520px; background: var(--w-card); display: grid; gap: 10px; }
.h3w.w-card .head { display: flex; align-items: center; gap: 8px; }
.h3w.w-card .head .name { font-weight: 600; font-size: 15px; }
.h3w.w-card .facts { display: flex; gap: 6px; flex-wrap: wrap; }

/* status-bar chip */
.h3w.w-chip { display: inline-flex; align-items: center; gap: 5px; height: 100%; padding: 0 6px; border: 0; background: transparent; cursor: pointer;
  font-size: 11px; color: var(--w-quiet); white-space: nowrap; border-radius: 4px; }
.h3w.w-chip:hover { color: var(--w-fg); background: var(--w-hover); }
.h3w.w-chip .d { width: 6px; height: 6px; border-radius: 50%; background: var(--tone); }
.h3w.w-chip.t-accent { color: var(--w-accent); font-weight: 600; }
`;import{Fragment as wf,jsx as ct,jsxs as $n}from"react/jsx-runtime";function Yi(){return ct("style",{children:ph})}function Nn({tone:n="neutral",children:e,outline:t}){return ct("span",{className:`w-tag t-${n}${t?" outline":""}`,children:e})}function Ko({p:n,groups:e,small:t}){let i=n?.group?.trim()||"";return ct("span",{className:`w-ava${t?" sm":""} g-${i?Ls(e,i):"other"}`,"aria-hidden":!0,children:Kc(n?.name)})}function Dn({p:n,groups:e}){let t=n?.name?.trim()||"someone",i=n?.group?.trim()||"";return $n("span",{className:"w-person",title:Wi(n),children:[ct("b",{children:t}),i?ct("span",{className:`grp g-${Ls(e,i)}`,children:ct("span",{children:i})}):null]})}function Zn({id:n,title:e,count:t,aside:i,children:s}){return $n("section",{"aria-labelledby":`w-sec-${n}`,"data-workshop-section":n,children:[$n("div",{className:"w-sec-head",children:[$n("h2",{id:`w-sec-${n}`,children:[e,t?ct("span",{className:"count num",children:t}):null]}),i?ct("div",{className:"aside",children:i}):null]}),s]})}function Ln({icon:n="check",children:e}){return $n("p",{className:"w-empty",children:[ct(Ie,{name:n}),ct("span",{children:e})]})}function Un({rest:n,fileRef:e,alt:t,className:i,fallback:s=null,onLoad:r}){let{file:a,loading:o}=Or(n,e);return o?ct("div",{className:`w-skel ${i??""}`,style:{width:"100%",height:"100%"},"aria-hidden":!0}):!a?.dataUrl||!/^data:image\//.test(a.dataUrl)?ct(wf,{children:s}):ct("img",{className:i,src:a.dataUrl,alt:t,draggable:!1,onLoad:r})}function gh({rest:n,fileRef:e,alt:t,icon:i="cube"}){return ct("span",{className:"w-thumb",children:e?ct(Un,{rest:n,fileRef:e,alt:t,fallback:ct(Ie,{name:i,size:18})}):ct(Ie,{name:i,size:18})})}function kr(){let[n,e]=Jo(null),[t,i]=Jo(null),s=vf(!1),r=xf(async a=>{if(!s.current){s.current=!0,e(a),i(null);try{let o=await fh(mh,a);i({...o,command:a}),o.kind==="failed"&&mh.notify({kind:"error",message:o.text})}finally{s.current=!1,e(null),Fs()}}},[]);return{busy:n,outcome:t,run:r,clear:()=>i(null)}}function Br({state:n,inline:e}){let t=n.outcome;if(!t)return null;let i=t.kind==="ran"?t.ok?"good":"warn":t.kind==="seated"?"accent":t.kind==="manual"?"warn":"bad",s=t.kind==="ran"&&t.ok?"check":t.kind==="seated"?"arrow":"alert";return $n("div",{className:`w-reply t-${i}${e?" w-reply-inline":""}`,role:"status","aria-live":"polite","data-workshop-reply":"",children:[ct(Ie,{name:s}),ct("pre",{children:t.text}),t.kind==="manual"?ct(yf,{text:`/${t.command.replace(/^\/+/,"")}`}):null,ct("button",{type:"button",className:"w-btn ghost sm",onClick:n.clear,"aria-label":"Dismiss the reply",children:ct(Ie,{name:"x",size:12})})]})}function yf({text:n}){let[e,t]=Jo(!1);return $n("button",{type:"button",className:"w-btn sm",onClick:()=>{try{navigator.clipboard?.writeText(n).then(()=>t(!0),()=>t(!1))}catch{t(!1)}},"aria-label":`Copy ${n}`,children:[ct(Ie,{name:e?"check":"copy",size:12})," ",e?"Copied":"Copy command"]})}function zr({text:n}){let e=n.split(/(`[^`]+`)/g);return ct("span",{children:e.map((t,i)=>t.startsWith("`")&&t.endsWith("`")&&t.length>2?ct("code",{children:t.slice(1,-1)},i):ct("span",{children:t},i))})}function Fn(){return $n("svg",{className:"w-spin",width:"14",height:"14",viewBox:"0 0 16 16","aria-hidden":!0,children:[ct("circle",{cx:"8",cy:"8",r:"6",fill:"none",stroke:"currentColor",strokeOpacity:".25",strokeWidth:"2"}),ct("path",{d:"M14 8a6 6 0 0 0-6-6",fill:"none",stroke:"currentColor",strokeWidth:"2",strokeLinecap:"round"})]})}import{Fragment as Sf,jsx as Vr,jsxs as _h}from"react/jsx-runtime";var Mf=15e3;function xh({rest:n,path:e}){let{ov:t,error:i,loading:s}=Xi(n,Mf);if(s)return null;let r,a;if(t){let o=Xc(t);r=o.text,a=o.tone}else{if(Us(i).kind!=="not_enabled")return null;r="Workshop off",a="neutral"}return _h(Sf,{children:[Vr(Yi,{}),_h("button",{type:"button",className:`h3w w-chip t-${a}`,onClick:()=>bf.navigate(e),title:`Workshop: ${r}`,"data-workshop-chip":"",children:[a==="neutral"?Vr(Ie,{name:"cube",size:12}):Vr("span",{className:"d","aria-hidden":!0}),Vr("span",{className:"num",children:r})]})]})}import{host as H0}from"@hermes/plugin-sdk";import{useEffect as G0,useState as Td}from"react";var jo=n=>{if(typeof n=="string")try{return jo(JSON.parse(n))}catch{return null}return n&&typeof n=="object"&&!Array.isArray(n)?n:null},Hr=n=>typeof n=="number"&&Number.isFinite(n)?n:null;function vh(n,e){let t=jo(n);if(!t||t.ok!==!0)return null;let i=jo(e)??{},s=typeof t.name=="string"&&t.name?t.name:typeof i.name=="string"?i.name:"",r=Hr(t.version);if(!s||r===null)return null;let a=Array.isArray(t.size_mm)&&t.size_mm.length===3&&t.size_mm.every(o=>typeof o=="number")?t.size_mm:null;return{slug:s,version:r,sizeMm:a,grams:Hr(t.est_grams_max),volumeCm3:Hr(t.volume_cm3),triangles:Hr(t.triangles),fitsBed:typeof t.fits_build_volume=="boolean"?t.fits_build_volume:null,warnings:Array.isArray(t.warnings)?t.warnings.filter(o=>typeof o=="string").slice(0,3):[],previews:Array.isArray(t.previews)?t.previews.filter(o=>typeof o=="string"):[]}}function yh(n,e){return n.previews.indexOf(e)<=0}function wh(n,e,t){let i=r=>r.trim().toLowerCase();return n.find(r=>i(r.slug)===i(e))?.versions.find(r=>r.version===t)??null}function bh(n){let e=[];return n.sizeMm&&e.push(`${n.sizeMm.map(t=>Math.round(t*10)/10).join(" \xD7 ")} mm`),n.grams!==null?e.push(`about ${Math.round(n.grams)} g`):n.volumeCm3!==null&&e.push(`${Math.round(n.volumeCm3*10)/10} cm\xB3`),n.fitsBed===!1&&e.push("too big for the bed"),e}import*as Ic from"@hermes/plugin-sdk";import{useEffect as As,useId as F0,useRef as bd,useState as Bo,useSyncExternalStore as O0}from"react";function Tf(){let n=null,e=new Set,t=()=>e.forEach(i=>i(n));return{claim(i){n!==i&&(n=i,t())},release(i){n===i&&(n=null,t())},holder:()=>n,subscribe(i){return e.add(i),()=>e.delete(i)}}}var Jn=Tf();var di={LEFT:0,MIDDLE:1,RIGHT:2,ROTATE:0,DOLLY:1,PAN:2},fi={ROTATE:0,PAN:1,DOLLY_PAN:2,DOLLY_ROTATE:3},Yh=0,kl=1,$h=2;var Bl=1,ka=2,En=3,Wn=0,Wt=1,An=2,Xn=0,Ai=1,zl=2,Vl=3,Hl=4,Zh=5,ri=100,Jh=101,Kh=102,jh=103,Qh=104,eu=200,tu=201,nu=202,iu=203,ua=204,da=205,su=206,ru=207,au=208,ou=209,lu=210,cu=211,hu=212,uu=213,du=214,Ba=0,za=1,Va=2,Ci=3,Ha=4,Ga=5,Wa=6,Xa=7,Gl=0,fu=1,pu=2,qn=0,mu=1,gu=2,_u=3,xu=4,vu=5,yu=6,wu=7;var Wl=300,Li=301,Ui=302,qa=303,Ya=304,Mr=306,fa=1e3,si=1001,pa=1002,on=1003,bu=1004;var Sr=1005;var gn=1006,$a=1007;var pi=1008;var vn=1009,Xl=1010,ql=1011,vs=1012,Za=1013,mi=1014,Cn=1015,ys=1016,Ja=1017,Ka=1018,ws=1020,Yl=35902,$l=35899,Zl=1021,Jl=1022,hn=1023,ls=1026,bs=1027,Kl=1028,ja=1029,jl=1030,Qa=1031;var eo=1033,Tr=33776,Er=33777,Ar=33778,Cr=33779,to=35840,no=35841,io=35842,so=35843,ro=36196,ao=37492,oo=37496,lo=37808,co=37809,ho=37810,uo=37811,fo=37812,po=37813,mo=37814,go=37815,_o=37816,xo=37817,vo=37818,yo=37819,wo=37820,bo=37821,Mo=36492,So=36494,To=36495,Eo=36283,Ao=36284,Co=36285,Ro=36286;var qs=2300,ma=2301,ha=2302,Sl=2400,Tl=2401,El=2402;var Mu=3200,Su=3201;var Ql=0,Tu=1,Yn="",It="srgb",Ri="srgb-linear",Ys="linear",ot="srgb";var Si=7680;var Al=519,Eu=512,Au=513,Cu=514,ec=515,Ru=516,Pu=517,Iu=518,Nu=519,Cl=35044;var tc="300 es",mn=2e3,$s=2001;var Mn=class{addEventListener(e,t){this._listeners===void 0&&(this._listeners={});let i=this._listeners;i[e]===void 0&&(i[e]=[]),i[e].indexOf(t)===-1&&i[e].push(t)}hasEventListener(e,t){let i=this._listeners;return i===void 0?!1:i[e]!==void 0&&i[e].indexOf(t)!==-1}removeEventListener(e,t){let i=this._listeners;if(i===void 0)return;let s=i[e];if(s!==void 0){let r=s.indexOf(t);r!==-1&&s.splice(r,1)}}dispatchEvent(e){let t=this._listeners;if(t===void 0)return;let i=t[e.type];if(i!==void 0){e.target=this;let s=i.slice(0);for(let r=0,a=s.length;r<a;r++)s[r].call(this,e);e.target=null}}},Dt=["00","01","02","03","04","05","06","07","08","09","0a","0b","0c","0d","0e","0f","10","11","12","13","14","15","16","17","18","19","1a","1b","1c","1d","1e","1f","20","21","22","23","24","25","26","27","28","29","2a","2b","2c","2d","2e","2f","30","31","32","33","34","35","36","37","38","39","3a","3b","3c","3d","3e","3f","40","41","42","43","44","45","46","47","48","49","4a","4b","4c","4d","4e","4f","50","51","52","53","54","55","56","57","58","59","5a","5b","5c","5d","5e","5f","60","61","62","63","64","65","66","67","68","69","6a","6b","6c","6d","6e","6f","70","71","72","73","74","75","76","77","78","79","7a","7b","7c","7d","7e","7f","80","81","82","83","84","85","86","87","88","89","8a","8b","8c","8d","8e","8f","90","91","92","93","94","95","96","97","98","99","9a","9b","9c","9d","9e","9f","a0","a1","a2","a3","a4","a5","a6","a7","a8","a9","aa","ab","ac","ad","ae","af","b0","b1","b2","b3","b4","b5","b6","b7","b8","b9","ba","bb","bc","bd","be","bf","c0","c1","c2","c3","c4","c5","c6","c7","c8","c9","ca","cb","cc","cd","ce","cf","d0","d1","d2","d3","d4","d5","d6","d7","d8","d9","da","db","dc","dd","de","df","e0","e1","e2","e3","e4","e5","e6","e7","e8","e9","ea","eb","ec","ed","ee","ef","f0","f1","f2","f3","f4","f5","f6","f7","f8","f9","fa","fb","fc","fd","fe","ff"],Mh=1234567,Hs=Math.PI/180,cs=180/Math.PI;function Fi(){let n=Math.random()*4294967295|0,e=Math.random()*4294967295|0,t=Math.random()*4294967295|0,i=Math.random()*4294967295|0;return(Dt[n&255]+Dt[n>>8&255]+Dt[n>>16&255]+Dt[n>>24&255]+"-"+Dt[e&255]+Dt[e>>8&255]+"-"+Dt[e>>16&15|64]+Dt[e>>24&255]+"-"+Dt[t&63|128]+Dt[t>>8&255]+"-"+Dt[t>>16&255]+Dt[t>>24&255]+Dt[i&255]+Dt[i>>8&255]+Dt[i>>16&255]+Dt[i>>24&255]).toLowerCase()}function Je(n,e,t){return Math.max(e,Math.min(t,n))}function nc(n,e){return(n%e+e)%e}function Ef(n,e,t,i,s){return i+(n-e)*(s-i)/(t-e)}function Af(n,e,t){return n!==e?(t-n)/(e-n):0}function Gs(n,e,t){return(1-t)*n+t*e}function Cf(n,e,t,i){return Gs(n,e,1-Math.exp(-t*i))}function Rf(n,e=1){return e-Math.abs(nc(n,e*2)-e)}function Pf(n,e,t){return n<=e?0:n>=t?1:(n=(n-e)/(t-e),n*n*(3-2*n))}function If(n,e,t){return n<=e?0:n>=t?1:(n=(n-e)/(t-e),n*n*n*(n*(n*6-15)+10))}function Nf(n,e){return n+Math.floor(Math.random()*(e-n+1))}function Df(n,e){return n+Math.random()*(e-n)}function Lf(n){return n*(.5-Math.random())}function Uf(n){n!==void 0&&(Mh=n);let e=Mh+=1831565813;return e=Math.imul(e^e>>>15,e|1),e^=e+Math.imul(e^e>>>7,e|61),((e^e>>>14)>>>0)/4294967296}function Ff(n){return n*Hs}function Of(n){return n*cs}function kf(n){return(n&n-1)===0&&n!==0}function Bf(n){return Math.pow(2,Math.ceil(Math.log(n)/Math.LN2))}function zf(n){return Math.pow(2,Math.floor(Math.log(n)/Math.LN2))}function Vf(n,e,t,i,s){let r=Math.cos,a=Math.sin,o=r(t/2),c=a(t/2),l=r((e+i)/2),u=a((e+i)/2),h=r((e-i)/2),d=a((e-i)/2),f=r((i-e)/2),g=a((i-e)/2);switch(s){case"XYX":n.set(o*u,c*h,c*d,o*l);break;case"YZY":n.set(c*d,o*u,c*h,o*l);break;case"ZXZ":n.set(c*h,c*d,o*u,o*l);break;case"XZX":n.set(o*u,c*g,c*f,o*l);break;case"YXY":n.set(c*f,o*u,c*g,o*l);break;case"ZYZ":n.set(c*g,c*f,o*u,o*l);break;default:console.warn("THREE.MathUtils: .setQuaternionFromProperEuler() encountered an unknown order: "+s)}}function as(n,e){switch(e.constructor){case Float32Array:return n;case Uint32Array:return n/4294967295;case Uint16Array:return n/65535;case Uint8Array:return n/255;case Int32Array:return Math.max(n/2147483647,-1);case Int16Array:return Math.max(n/32767,-1);case Int8Array:return Math.max(n/127,-1);default:throw new Error("Invalid component type.")}}function Ht(n,e){switch(e.constructor){case Float32Array:return n;case Uint32Array:return Math.round(n*4294967295);case Uint16Array:return Math.round(n*65535);case Uint8Array:return Math.round(n*255);case Int32Array:return Math.round(n*2147483647);case Int16Array:return Math.round(n*32767);case Int8Array:return Math.round(n*127);default:throw new Error("Invalid component type.")}}var ic={DEG2RAD:Hs,RAD2DEG:cs,generateUUID:Fi,clamp:Je,euclideanModulo:nc,mapLinear:Ef,inverseLerp:Af,lerp:Gs,damp:Cf,pingpong:Rf,smoothstep:Pf,smootherstep:If,randInt:Nf,randFloat:Df,randFloatSpread:Lf,seededRandom:Uf,degToRad:Ff,radToDeg:Of,isPowerOfTwo:kf,ceilPowerOfTwo:Bf,floorPowerOfTwo:zf,setQuaternionFromProperEuler:Vf,normalize:Ht,denormalize:as},de=class n{constructor(e=0,t=0){n.prototype.isVector2=!0,this.x=e,this.y=t}get width(){return this.x}set width(e){this.x=e}get height(){return this.y}set height(e){this.y=e}set(e,t){return this.x=e,this.y=t,this}setScalar(e){return this.x=e,this.y=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y)}copy(e){return this.x=e.x,this.y=e.y,this}add(e){return this.x+=e.x,this.y+=e.y,this}addScalar(e){return this.x+=e,this.y+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this}subScalar(e){return this.x-=e,this.y-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this}multiply(e){return this.x*=e.x,this.y*=e.y,this}multiplyScalar(e){return this.x*=e,this.y*=e,this}divide(e){return this.x/=e.x,this.y/=e.y,this}divideScalar(e){return this.multiplyScalar(1/e)}applyMatrix3(e){let t=this.x,i=this.y,s=e.elements;return this.x=s[0]*t+s[3]*i+s[6],this.y=s[1]*t+s[4]*i+s[7],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this}clamp(e,t){return this.x=Je(this.x,e.x,t.x),this.y=Je(this.y,e.y,t.y),this}clampScalar(e,t){return this.x=Je(this.x,e,t),this.y=Je(this.y,e,t),this}clampLength(e,t){let i=this.length();return this.divideScalar(i||1).multiplyScalar(Je(i,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this}negate(){return this.x=-this.x,this.y=-this.y,this}dot(e){return this.x*e.x+this.y*e.y}cross(e){return this.x*e.y-this.y*e.x}lengthSq(){return this.x*this.x+this.y*this.y}length(){return Math.sqrt(this.x*this.x+this.y*this.y)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)}normalize(){return this.divideScalar(this.length()||1)}angle(){return Math.atan2(-this.y,-this.x)+Math.PI}angleTo(e){let t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;let i=this.dot(e)/t;return Math.acos(Je(i,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){let t=this.x-e.x,i=this.y-e.y;return t*t+i*i}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this}lerpVectors(e,t,i){return this.x=e.x+(t.x-e.x)*i,this.y=e.y+(t.y-e.y)*i,this}equals(e){return e.x===this.x&&e.y===this.y}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this}rotateAround(e,t){let i=Math.cos(t),s=Math.sin(t),r=this.x-e.x,a=this.y-e.y;return this.x=r*i-a*s+e.x,this.y=r*s+a*i+e.y,this}random(){return this.x=Math.random(),this.y=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y}},ln=class{constructor(e=0,t=0,i=0,s=1){this.isQuaternion=!0,this._x=e,this._y=t,this._z=i,this._w=s}static slerpFlat(e,t,i,s,r,a,o){let c=i[s+0],l=i[s+1],u=i[s+2],h=i[s+3],d=r[a+0],f=r[a+1],g=r[a+2],x=r[a+3];if(o===0){e[t+0]=c,e[t+1]=l,e[t+2]=u,e[t+3]=h;return}if(o===1){e[t+0]=d,e[t+1]=f,e[t+2]=g,e[t+3]=x;return}if(h!==x||c!==d||l!==f||u!==g){let m=1-o,p=c*d+l*f+u*g+h*x,T=p>=0?1:-1,M=1-p*p;if(M>Number.EPSILON){let R=Math.sqrt(M),E=Math.atan2(R,p*T);m=Math.sin(m*E)/R,o=Math.sin(o*E)/R}let y=o*T;if(c=c*m+d*y,l=l*m+f*y,u=u*m+g*y,h=h*m+x*y,m===1-o){let R=1/Math.sqrt(c*c+l*l+u*u+h*h);c*=R,l*=R,u*=R,h*=R}}e[t]=c,e[t+1]=l,e[t+2]=u,e[t+3]=h}static multiplyQuaternionsFlat(e,t,i,s,r,a){let o=i[s],c=i[s+1],l=i[s+2],u=i[s+3],h=r[a],d=r[a+1],f=r[a+2],g=r[a+3];return e[t]=o*g+u*h+c*f-l*d,e[t+1]=c*g+u*d+l*h-o*f,e[t+2]=l*g+u*f+o*d-c*h,e[t+3]=u*g-o*h-c*d-l*f,e}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get w(){return this._w}set w(e){this._w=e,this._onChangeCallback()}set(e,t,i,s){return this._x=e,this._y=t,this._z=i,this._w=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._w)}copy(e){return this._x=e.x,this._y=e.y,this._z=e.z,this._w=e.w,this._onChangeCallback(),this}setFromEuler(e,t=!0){let i=e._x,s=e._y,r=e._z,a=e._order,o=Math.cos,c=Math.sin,l=o(i/2),u=o(s/2),h=o(r/2),d=c(i/2),f=c(s/2),g=c(r/2);switch(a){case"XYZ":this._x=d*u*h+l*f*g,this._y=l*f*h-d*u*g,this._z=l*u*g+d*f*h,this._w=l*u*h-d*f*g;break;case"YXZ":this._x=d*u*h+l*f*g,this._y=l*f*h-d*u*g,this._z=l*u*g-d*f*h,this._w=l*u*h+d*f*g;break;case"ZXY":this._x=d*u*h-l*f*g,this._y=l*f*h+d*u*g,this._z=l*u*g+d*f*h,this._w=l*u*h-d*f*g;break;case"ZYX":this._x=d*u*h-l*f*g,this._y=l*f*h+d*u*g,this._z=l*u*g-d*f*h,this._w=l*u*h+d*f*g;break;case"YZX":this._x=d*u*h+l*f*g,this._y=l*f*h+d*u*g,this._z=l*u*g-d*f*h,this._w=l*u*h-d*f*g;break;case"XZY":this._x=d*u*h-l*f*g,this._y=l*f*h-d*u*g,this._z=l*u*g+d*f*h,this._w=l*u*h+d*f*g;break;default:console.warn("THREE.Quaternion: .setFromEuler() encountered an unknown order: "+a)}return t===!0&&this._onChangeCallback(),this}setFromAxisAngle(e,t){let i=t/2,s=Math.sin(i);return this._x=e.x*s,this._y=e.y*s,this._z=e.z*s,this._w=Math.cos(i),this._onChangeCallback(),this}setFromRotationMatrix(e){let t=e.elements,i=t[0],s=t[4],r=t[8],a=t[1],o=t[5],c=t[9],l=t[2],u=t[6],h=t[10],d=i+o+h;if(d>0){let f=.5/Math.sqrt(d+1);this._w=.25/f,this._x=(u-c)*f,this._y=(r-l)*f,this._z=(a-s)*f}else if(i>o&&i>h){let f=2*Math.sqrt(1+i-o-h);this._w=(u-c)/f,this._x=.25*f,this._y=(s+a)/f,this._z=(r+l)/f}else if(o>h){let f=2*Math.sqrt(1+o-i-h);this._w=(r-l)/f,this._x=(s+a)/f,this._y=.25*f,this._z=(c+u)/f}else{let f=2*Math.sqrt(1+h-i-o);this._w=(a-s)/f,this._x=(r+l)/f,this._y=(c+u)/f,this._z=.25*f}return this._onChangeCallback(),this}setFromUnitVectors(e,t){let i=e.dot(t)+1;return i<1e-8?(i=0,Math.abs(e.x)>Math.abs(e.z)?(this._x=-e.y,this._y=e.x,this._z=0,this._w=i):(this._x=0,this._y=-e.z,this._z=e.y,this._w=i)):(this._x=e.y*t.z-e.z*t.y,this._y=e.z*t.x-e.x*t.z,this._z=e.x*t.y-e.y*t.x,this._w=i),this.normalize()}angleTo(e){return 2*Math.acos(Math.abs(Je(this.dot(e),-1,1)))}rotateTowards(e,t){let i=this.angleTo(e);if(i===0)return this;let s=Math.min(1,t/i);return this.slerp(e,s),this}identity(){return this.set(0,0,0,1)}invert(){return this.conjugate()}conjugate(){return this._x*=-1,this._y*=-1,this._z*=-1,this._onChangeCallback(),this}dot(e){return this._x*e._x+this._y*e._y+this._z*e._z+this._w*e._w}lengthSq(){return this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w}length(){return Math.sqrt(this._x*this._x+this._y*this._y+this._z*this._z+this._w*this._w)}normalize(){let e=this.length();return e===0?(this._x=0,this._y=0,this._z=0,this._w=1):(e=1/e,this._x=this._x*e,this._y=this._y*e,this._z=this._z*e,this._w=this._w*e),this._onChangeCallback(),this}multiply(e){return this.multiplyQuaternions(this,e)}premultiply(e){return this.multiplyQuaternions(e,this)}multiplyQuaternions(e,t){let i=e._x,s=e._y,r=e._z,a=e._w,o=t._x,c=t._y,l=t._z,u=t._w;return this._x=i*u+a*o+s*l-r*c,this._y=s*u+a*c+r*o-i*l,this._z=r*u+a*l+i*c-s*o,this._w=a*u-i*o-s*c-r*l,this._onChangeCallback(),this}slerp(e,t){if(t===0)return this;if(t===1)return this.copy(e);let i=this._x,s=this._y,r=this._z,a=this._w,o=a*e._w+i*e._x+s*e._y+r*e._z;if(o<0?(this._w=-e._w,this._x=-e._x,this._y=-e._y,this._z=-e._z,o=-o):this.copy(e),o>=1)return this._w=a,this._x=i,this._y=s,this._z=r,this;let c=1-o*o;if(c<=Number.EPSILON){let f=1-t;return this._w=f*a+t*this._w,this._x=f*i+t*this._x,this._y=f*s+t*this._y,this._z=f*r+t*this._z,this.normalize(),this}let l=Math.sqrt(c),u=Math.atan2(l,o),h=Math.sin((1-t)*u)/l,d=Math.sin(t*u)/l;return this._w=a*h+this._w*d,this._x=i*h+this._x*d,this._y=s*h+this._y*d,this._z=r*h+this._z*d,this._onChangeCallback(),this}slerpQuaternions(e,t,i){return this.copy(e).slerp(t,i)}random(){let e=2*Math.PI*Math.random(),t=2*Math.PI*Math.random(),i=Math.random(),s=Math.sqrt(1-i),r=Math.sqrt(i);return this.set(s*Math.sin(e),s*Math.cos(e),r*Math.sin(t),r*Math.cos(t))}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._w===this._w}fromArray(e,t=0){return this._x=e[t],this._y=e[t+1],this._z=e[t+2],this._w=e[t+3],this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._w,e}fromBufferAttribute(e,t){return this._x=e.getX(t),this._y=e.getY(t),this._z=e.getZ(t),this._w=e.getW(t),this._onChangeCallback(),this}toJSON(){return this.toArray()}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._w}},N=class n{constructor(e=0,t=0,i=0){n.prototype.isVector3=!0,this.x=e,this.y=t,this.z=i}set(e,t,i){return i===void 0&&(i=this.z),this.x=e,this.y=t,this.z=i,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this}multiplyVectors(e,t){return this.x=e.x*t.x,this.y=e.y*t.y,this.z=e.z*t.z,this}applyEuler(e){return this.applyQuaternion(Sh.setFromEuler(e))}applyAxisAngle(e,t){return this.applyQuaternion(Sh.setFromAxisAngle(e,t))}applyMatrix3(e){let t=this.x,i=this.y,s=this.z,r=e.elements;return this.x=r[0]*t+r[3]*i+r[6]*s,this.y=r[1]*t+r[4]*i+r[7]*s,this.z=r[2]*t+r[5]*i+r[8]*s,this}applyNormalMatrix(e){return this.applyMatrix3(e).normalize()}applyMatrix4(e){let t=this.x,i=this.y,s=this.z,r=e.elements,a=1/(r[3]*t+r[7]*i+r[11]*s+r[15]);return this.x=(r[0]*t+r[4]*i+r[8]*s+r[12])*a,this.y=(r[1]*t+r[5]*i+r[9]*s+r[13])*a,this.z=(r[2]*t+r[6]*i+r[10]*s+r[14])*a,this}applyQuaternion(e){let t=this.x,i=this.y,s=this.z,r=e.x,a=e.y,o=e.z,c=e.w,l=2*(a*s-o*i),u=2*(o*t-r*s),h=2*(r*i-a*t);return this.x=t+c*l+a*h-o*u,this.y=i+c*u+o*l-r*h,this.z=s+c*h+r*u-a*l,this}project(e){return this.applyMatrix4(e.matrixWorldInverse).applyMatrix4(e.projectionMatrix)}unproject(e){return this.applyMatrix4(e.projectionMatrixInverse).applyMatrix4(e.matrixWorld)}transformDirection(e){let t=this.x,i=this.y,s=this.z,r=e.elements;return this.x=r[0]*t+r[4]*i+r[8]*s,this.y=r[1]*t+r[5]*i+r[9]*s,this.z=r[2]*t+r[6]*i+r[10]*s,this.normalize()}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this}divideScalar(e){return this.multiplyScalar(1/e)}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this}clamp(e,t){return this.x=Je(this.x,e.x,t.x),this.y=Je(this.y,e.y,t.y),this.z=Je(this.z,e.z,t.z),this}clampScalar(e,t){return this.x=Je(this.x,e,t),this.y=Je(this.y,e,t),this.z=Je(this.z,e,t),this}clampLength(e,t){let i=this.length();return this.divideScalar(i||1).multiplyScalar(Je(i,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this}lerpVectors(e,t,i){return this.x=e.x+(t.x-e.x)*i,this.y=e.y+(t.y-e.y)*i,this.z=e.z+(t.z-e.z)*i,this}cross(e){return this.crossVectors(this,e)}crossVectors(e,t){let i=e.x,s=e.y,r=e.z,a=t.x,o=t.y,c=t.z;return this.x=s*c-r*o,this.y=r*a-i*c,this.z=i*o-s*a,this}projectOnVector(e){let t=e.lengthSq();if(t===0)return this.set(0,0,0);let i=e.dot(this)/t;return this.copy(e).multiplyScalar(i)}projectOnPlane(e){return Qo.copy(this).projectOnVector(e),this.sub(Qo)}reflect(e){return this.sub(Qo.copy(e).multiplyScalar(2*this.dot(e)))}angleTo(e){let t=Math.sqrt(this.lengthSq()*e.lengthSq());if(t===0)return Math.PI/2;let i=this.dot(e)/t;return Math.acos(Je(i,-1,1))}distanceTo(e){return Math.sqrt(this.distanceToSquared(e))}distanceToSquared(e){let t=this.x-e.x,i=this.y-e.y,s=this.z-e.z;return t*t+i*i+s*s}manhattanDistanceTo(e){return Math.abs(this.x-e.x)+Math.abs(this.y-e.y)+Math.abs(this.z-e.z)}setFromSpherical(e){return this.setFromSphericalCoords(e.radius,e.phi,e.theta)}setFromSphericalCoords(e,t,i){let s=Math.sin(t)*e;return this.x=s*Math.sin(i),this.y=Math.cos(t)*e,this.z=s*Math.cos(i),this}setFromCylindrical(e){return this.setFromCylindricalCoords(e.radius,e.theta,e.y)}setFromCylindricalCoords(e,t,i){return this.x=e*Math.sin(t),this.y=i,this.z=e*Math.cos(t),this}setFromMatrixPosition(e){let t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this}setFromMatrixScale(e){let t=this.setFromMatrixColumn(e,0).length(),i=this.setFromMatrixColumn(e,1).length(),s=this.setFromMatrixColumn(e,2).length();return this.x=t,this.y=i,this.z=s,this}setFromMatrixColumn(e,t){return this.fromArray(e.elements,t*4)}setFromMatrix3Column(e,t){return this.fromArray(e.elements,t*3)}setFromEuler(e){return this.x=e._x,this.y=e._y,this.z=e._z,this}setFromColor(e){return this.x=e.r,this.y=e.g,this.z=e.b,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this}randomDirection(){let e=Math.random()*Math.PI*2,t=Math.random()*2-1,i=Math.sqrt(1-t*t);return this.x=i*Math.cos(e),this.y=t,this.z=i*Math.sin(e),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z}},Qo=new N,Sh=new ln,$e=class n{constructor(e,t,i,s,r,a,o,c,l){n.prototype.isMatrix3=!0,this.elements=[1,0,0,0,1,0,0,0,1],e!==void 0&&this.set(e,t,i,s,r,a,o,c,l)}set(e,t,i,s,r,a,o,c,l){let u=this.elements;return u[0]=e,u[1]=s,u[2]=o,u[3]=t,u[4]=r,u[5]=c,u[6]=i,u[7]=a,u[8]=l,this}identity(){return this.set(1,0,0,0,1,0,0,0,1),this}copy(e){let t=this.elements,i=e.elements;return t[0]=i[0],t[1]=i[1],t[2]=i[2],t[3]=i[3],t[4]=i[4],t[5]=i[5],t[6]=i[6],t[7]=i[7],t[8]=i[8],this}extractBasis(e,t,i){return e.setFromMatrix3Column(this,0),t.setFromMatrix3Column(this,1),i.setFromMatrix3Column(this,2),this}setFromMatrix4(e){let t=e.elements;return this.set(t[0],t[4],t[8],t[1],t[5],t[9],t[2],t[6],t[10]),this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){let i=e.elements,s=t.elements,r=this.elements,a=i[0],o=i[3],c=i[6],l=i[1],u=i[4],h=i[7],d=i[2],f=i[5],g=i[8],x=s[0],m=s[3],p=s[6],T=s[1],M=s[4],y=s[7],R=s[2],E=s[5],P=s[8];return r[0]=a*x+o*T+c*R,r[3]=a*m+o*M+c*E,r[6]=a*p+o*y+c*P,r[1]=l*x+u*T+h*R,r[4]=l*m+u*M+h*E,r[7]=l*p+u*y+h*P,r[2]=d*x+f*T+g*R,r[5]=d*m+f*M+g*E,r[8]=d*p+f*y+g*P,this}multiplyScalar(e){let t=this.elements;return t[0]*=e,t[3]*=e,t[6]*=e,t[1]*=e,t[4]*=e,t[7]*=e,t[2]*=e,t[5]*=e,t[8]*=e,this}determinant(){let e=this.elements,t=e[0],i=e[1],s=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],u=e[8];return t*a*u-t*o*l-i*r*u+i*o*c+s*r*l-s*a*c}invert(){let e=this.elements,t=e[0],i=e[1],s=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],u=e[8],h=u*a-o*l,d=o*c-u*r,f=l*r-a*c,g=t*h+i*d+s*f;if(g===0)return this.set(0,0,0,0,0,0,0,0,0);let x=1/g;return e[0]=h*x,e[1]=(s*l-u*i)*x,e[2]=(o*i-s*a)*x,e[3]=d*x,e[4]=(u*t-s*c)*x,e[5]=(s*r-o*t)*x,e[6]=f*x,e[7]=(i*c-l*t)*x,e[8]=(a*t-i*r)*x,this}transpose(){let e,t=this.elements;return e=t[1],t[1]=t[3],t[3]=e,e=t[2],t[2]=t[6],t[6]=e,e=t[5],t[5]=t[7],t[7]=e,this}getNormalMatrix(e){return this.setFromMatrix4(e).invert().transpose()}transposeIntoArray(e){let t=this.elements;return e[0]=t[0],e[1]=t[3],e[2]=t[6],e[3]=t[1],e[4]=t[4],e[5]=t[7],e[6]=t[2],e[7]=t[5],e[8]=t[8],this}setUvTransform(e,t,i,s,r,a,o){let c=Math.cos(r),l=Math.sin(r);return this.set(i*c,i*l,-i*(c*a+l*o)+a+e,-s*l,s*c,-s*(-l*a+c*o)+o+t,0,0,1),this}scale(e,t){return this.premultiply(el.makeScale(e,t)),this}rotate(e){return this.premultiply(el.makeRotation(-e)),this}translate(e,t){return this.premultiply(el.makeTranslation(e,t)),this}makeTranslation(e,t){return e.isVector2?this.set(1,0,e.x,0,1,e.y,0,0,1):this.set(1,0,e,0,1,t,0,0,1),this}makeRotation(e){let t=Math.cos(e),i=Math.sin(e);return this.set(t,-i,0,i,t,0,0,0,1),this}makeScale(e,t){return this.set(e,0,0,0,t,0,0,0,1),this}equals(e){let t=this.elements,i=e.elements;for(let s=0;s<9;s++)if(t[s]!==i[s])return!1;return!0}fromArray(e,t=0){for(let i=0;i<9;i++)this.elements[i]=e[i+t];return this}toArray(e=[],t=0){let i=this.elements;return e[t]=i[0],e[t+1]=i[1],e[t+2]=i[2],e[t+3]=i[3],e[t+4]=i[4],e[t+5]=i[5],e[t+6]=i[6],e[t+7]=i[7],e[t+8]=i[8],e}clone(){return new this.constructor().fromArray(this.elements)}},el=new $e;function sc(n){for(let e=n.length-1;e>=0;--e)if(n[e]>=65535)return!0;return!1}function Zs(n){return document.createElementNS("http://www.w3.org/1999/xhtml",n)}function Du(){let n=Zs("canvas");return n.style.display="block",n}var Th={};function hs(n){n in Th||(Th[n]=!0,console.warn(n))}function Lu(n,e,t){return new Promise(function(i,s){function r(){switch(n.clientWaitSync(e,n.SYNC_FLUSH_COMMANDS_BIT,0)){case n.WAIT_FAILED:s();break;case n.TIMEOUT_EXPIRED:setTimeout(r,t);break;default:i()}}setTimeout(r,t)})}var Eh=new $e().set(.4123908,.3575843,.1804808,.212639,.7151687,.0721923,.0193308,.1191948,.9505322),Ah=new $e().set(3.2409699,-1.5373832,-.4986108,-.9692436,1.8759675,.0415551,.0556301,-.203977,1.0569715);function Hf(){let n={enabled:!0,workingColorSpace:Ri,spaces:{},convert:function(s,r,a){return this.enabled===!1||r===a||!r||!a||(this.spaces[r].transfer===ot&&(s.r=Gn(s.r),s.g=Gn(s.g),s.b=Gn(s.b)),this.spaces[r].primaries!==this.spaces[a].primaries&&(s.applyMatrix3(this.spaces[r].toXYZ),s.applyMatrix3(this.spaces[a].fromXYZ)),this.spaces[a].transfer===ot&&(s.r=os(s.r),s.g=os(s.g),s.b=os(s.b))),s},workingToColorSpace:function(s,r){return this.convert(s,this.workingColorSpace,r)},colorSpaceToWorking:function(s,r){return this.convert(s,r,this.workingColorSpace)},getPrimaries:function(s){return this.spaces[s].primaries},getTransfer:function(s){return s===Yn?Ys:this.spaces[s].transfer},getToneMappingMode:function(s){return this.spaces[s].outputColorSpaceConfig.toneMappingMode||"standard"},getLuminanceCoefficients:function(s,r=this.workingColorSpace){return s.fromArray(this.spaces[r].luminanceCoefficients)},define:function(s){Object.assign(this.spaces,s)},_getMatrix:function(s,r,a){return s.copy(this.spaces[r].toXYZ).multiply(this.spaces[a].fromXYZ)},_getDrawingBufferColorSpace:function(s){return this.spaces[s].outputColorSpaceConfig.drawingBufferColorSpace},_getUnpackColorSpace:function(s=this.workingColorSpace){return this.spaces[s].workingColorSpaceConfig.unpackColorSpace},fromWorkingColorSpace:function(s,r){return hs("THREE.ColorManagement: .fromWorkingColorSpace() has been renamed to .workingToColorSpace()."),n.workingToColorSpace(s,r)},toWorkingColorSpace:function(s,r){return hs("THREE.ColorManagement: .toWorkingColorSpace() has been renamed to .colorSpaceToWorking()."),n.colorSpaceToWorking(s,r)}},e=[.64,.33,.3,.6,.15,.06],t=[.2126,.7152,.0722],i=[.3127,.329];return n.define({[Ri]:{primaries:e,whitePoint:i,transfer:Ys,toXYZ:Eh,fromXYZ:Ah,luminanceCoefficients:t,workingColorSpaceConfig:{unpackColorSpace:It},outputColorSpaceConfig:{drawingBufferColorSpace:It}},[It]:{primaries:e,whitePoint:i,transfer:ot,toXYZ:Eh,fromXYZ:Ah,luminanceCoefficients:t,outputColorSpaceConfig:{drawingBufferColorSpace:It}}}),n}var st=Hf();function Gn(n){return n<.04045?n*.0773993808:Math.pow(n*.9478672986+.0521327014,2.4)}function os(n){return n<.0031308?n*12.92:1.055*Math.pow(n,.41666)-.055}var $i,ga=class{static getDataURL(e,t="image/png"){if(/^data:/i.test(e.src)||typeof HTMLCanvasElement>"u")return e.src;let i;if(e instanceof HTMLCanvasElement)i=e;else{$i===void 0&&($i=Zs("canvas")),$i.width=e.width,$i.height=e.height;let s=$i.getContext("2d");e instanceof ImageData?s.putImageData(e,0,0):s.drawImage(e,0,0,e.width,e.height),i=$i}return i.toDataURL(t)}static sRGBToLinear(e){if(typeof HTMLImageElement<"u"&&e instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&e instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&e instanceof ImageBitmap){let t=Zs("canvas");t.width=e.width,t.height=e.height;let i=t.getContext("2d");i.drawImage(e,0,0,e.width,e.height);let s=i.getImageData(0,0,e.width,e.height),r=s.data;for(let a=0;a<r.length;a++)r[a]=Gn(r[a]/255)*255;return i.putImageData(s,0,0),t}else if(e.data){let t=e.data.slice(0);for(let i=0;i<t.length;i++)t instanceof Uint8Array||t instanceof Uint8ClampedArray?t[i]=Math.floor(Gn(t[i]/255)*255):t[i]=Gn(t[i]);return{data:t,width:e.width,height:e.height}}else return console.warn("THREE.ImageUtils.sRGBToLinear(): Unsupported image type. No color space conversion applied."),e}},Gf=0,us=class{constructor(e=null){this.isSource=!0,Object.defineProperty(this,"id",{value:Gf++}),this.uuid=Fi(),this.data=e,this.dataReady=!0,this.version=0}getSize(e){let t=this.data;return typeof HTMLVideoElement<"u"&&t instanceof HTMLVideoElement?e.set(t.videoWidth,t.videoHeight,0):t instanceof VideoFrame?e.set(t.displayHeight,t.displayWidth,0):t!==null?e.set(t.width,t.height,t.depth||0):e.set(0,0,0),e}set needsUpdate(e){e===!0&&this.version++}toJSON(e){let t=e===void 0||typeof e=="string";if(!t&&e.images[this.uuid]!==void 0)return e.images[this.uuid];let i={uuid:this.uuid,url:""},s=this.data;if(s!==null){let r;if(Array.isArray(s)){r=[];for(let a=0,o=s.length;a<o;a++)s[a].isDataTexture?r.push(tl(s[a].image)):r.push(tl(s[a]))}else r=tl(s);i.url=r}return t||(e.images[this.uuid]=i),i}};function tl(n){return typeof HTMLImageElement<"u"&&n instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&n instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&n instanceof ImageBitmap?ga.getDataURL(n):n.data?{data:Array.from(n.data),width:n.width,height:n.height,type:n.data.constructor.name}:(console.warn("THREE.Texture: Unable to serialize Texture."),{})}var Wf=0,nl=new N,Yt=class n extends Mn{constructor(e=n.DEFAULT_IMAGE,t=n.DEFAULT_MAPPING,i=si,s=si,r=gn,a=pi,o=hn,c=vn,l=n.DEFAULT_ANISOTROPY,u=Yn){super(),this.isTexture=!0,Object.defineProperty(this,"id",{value:Wf++}),this.uuid=Fi(),this.name="",this.source=new us(e),this.mipmaps=[],this.mapping=t,this.channel=0,this.wrapS=i,this.wrapT=s,this.magFilter=r,this.minFilter=a,this.anisotropy=l,this.format=o,this.internalFormat=null,this.type=c,this.offset=new de(0,0),this.repeat=new de(1,1),this.center=new de(0,0),this.rotation=0,this.matrixAutoUpdate=!0,this.matrix=new $e,this.generateMipmaps=!0,this.premultiplyAlpha=!1,this.flipY=!0,this.unpackAlignment=4,this.colorSpace=u,this.userData={},this.updateRanges=[],this.version=0,this.onUpdate=null,this.renderTarget=null,this.isRenderTargetTexture=!1,this.isArrayTexture=!!(e&&e.depth&&e.depth>1),this.pmremVersion=0}get width(){return this.source.getSize(nl).x}get height(){return this.source.getSize(nl).y}get depth(){return this.source.getSize(nl).z}get image(){return this.source.data}set image(e=null){this.source.data=e}updateMatrix(){this.matrix.setUvTransform(this.offset.x,this.offset.y,this.repeat.x,this.repeat.y,this.rotation,this.center.x,this.center.y)}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}clone(){return new this.constructor().copy(this)}copy(e){return this.name=e.name,this.source=e.source,this.mipmaps=e.mipmaps.slice(0),this.mapping=e.mapping,this.channel=e.channel,this.wrapS=e.wrapS,this.wrapT=e.wrapT,this.magFilter=e.magFilter,this.minFilter=e.minFilter,this.anisotropy=e.anisotropy,this.format=e.format,this.internalFormat=e.internalFormat,this.type=e.type,this.offset.copy(e.offset),this.repeat.copy(e.repeat),this.center.copy(e.center),this.rotation=e.rotation,this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrix.copy(e.matrix),this.generateMipmaps=e.generateMipmaps,this.premultiplyAlpha=e.premultiplyAlpha,this.flipY=e.flipY,this.unpackAlignment=e.unpackAlignment,this.colorSpace=e.colorSpace,this.renderTarget=e.renderTarget,this.isRenderTargetTexture=e.isRenderTargetTexture,this.isArrayTexture=e.isArrayTexture,this.userData=JSON.parse(JSON.stringify(e.userData)),this.needsUpdate=!0,this}setValues(e){for(let t in e){let i=e[t];if(i===void 0){console.warn(`THREE.Texture.setValues(): parameter '${t}' has value of undefined.`);continue}let s=this[t];if(s===void 0){console.warn(`THREE.Texture.setValues(): property '${t}' does not exist.`);continue}s&&i&&s.isVector2&&i.isVector2||s&&i&&s.isVector3&&i.isVector3||s&&i&&s.isMatrix3&&i.isMatrix3?s.copy(i):this[t]=i}}toJSON(e){let t=e===void 0||typeof e=="string";if(!t&&e.textures[this.uuid]!==void 0)return e.textures[this.uuid];let i={metadata:{version:4.7,type:"Texture",generator:"Texture.toJSON"},uuid:this.uuid,name:this.name,image:this.source.toJSON(e).uuid,mapping:this.mapping,channel:this.channel,repeat:[this.repeat.x,this.repeat.y],offset:[this.offset.x,this.offset.y],center:[this.center.x,this.center.y],rotation:this.rotation,wrap:[this.wrapS,this.wrapT],format:this.format,internalFormat:this.internalFormat,type:this.type,colorSpace:this.colorSpace,minFilter:this.minFilter,magFilter:this.magFilter,anisotropy:this.anisotropy,flipY:this.flipY,generateMipmaps:this.generateMipmaps,premultiplyAlpha:this.premultiplyAlpha,unpackAlignment:this.unpackAlignment};return Object.keys(this.userData).length>0&&(i.userData=this.userData),t||(e.textures[this.uuid]=i),i}dispose(){this.dispatchEvent({type:"dispose"})}transformUv(e){if(this.mapping!==Wl)return e;if(e.applyMatrix3(this.matrix),e.x<0||e.x>1)switch(this.wrapS){case fa:e.x=e.x-Math.floor(e.x);break;case si:e.x=e.x<0?0:1;break;case pa:Math.abs(Math.floor(e.x)%2)===1?e.x=Math.ceil(e.x)-e.x:e.x=e.x-Math.floor(e.x);break}if(e.y<0||e.y>1)switch(this.wrapT){case fa:e.y=e.y-Math.floor(e.y);break;case si:e.y=e.y<0?0:1;break;case pa:Math.abs(Math.floor(e.y)%2)===1?e.y=Math.ceil(e.y)-e.y:e.y=e.y-Math.floor(e.y);break}return this.flipY&&(e.y=1-e.y),e}set needsUpdate(e){e===!0&&(this.version++,this.source.needsUpdate=!0)}set needsPMREMUpdate(e){e===!0&&this.pmremVersion++}};Yt.DEFAULT_IMAGE=null;Yt.DEFAULT_MAPPING=Wl;Yt.DEFAULT_ANISOTROPY=1;var wt=class n{constructor(e=0,t=0,i=0,s=1){n.prototype.isVector4=!0,this.x=e,this.y=t,this.z=i,this.w=s}get width(){return this.z}set width(e){this.z=e}get height(){return this.w}set height(e){this.w=e}set(e,t,i,s){return this.x=e,this.y=t,this.z=i,this.w=s,this}setScalar(e){return this.x=e,this.y=e,this.z=e,this.w=e,this}setX(e){return this.x=e,this}setY(e){return this.y=e,this}setZ(e){return this.z=e,this}setW(e){return this.w=e,this}setComponent(e,t){switch(e){case 0:this.x=t;break;case 1:this.y=t;break;case 2:this.z=t;break;case 3:this.w=t;break;default:throw new Error("index is out of range: "+e)}return this}getComponent(e){switch(e){case 0:return this.x;case 1:return this.y;case 2:return this.z;case 3:return this.w;default:throw new Error("index is out of range: "+e)}}clone(){return new this.constructor(this.x,this.y,this.z,this.w)}copy(e){return this.x=e.x,this.y=e.y,this.z=e.z,this.w=e.w!==void 0?e.w:1,this}add(e){return this.x+=e.x,this.y+=e.y,this.z+=e.z,this.w+=e.w,this}addScalar(e){return this.x+=e,this.y+=e,this.z+=e,this.w+=e,this}addVectors(e,t){return this.x=e.x+t.x,this.y=e.y+t.y,this.z=e.z+t.z,this.w=e.w+t.w,this}addScaledVector(e,t){return this.x+=e.x*t,this.y+=e.y*t,this.z+=e.z*t,this.w+=e.w*t,this}sub(e){return this.x-=e.x,this.y-=e.y,this.z-=e.z,this.w-=e.w,this}subScalar(e){return this.x-=e,this.y-=e,this.z-=e,this.w-=e,this}subVectors(e,t){return this.x=e.x-t.x,this.y=e.y-t.y,this.z=e.z-t.z,this.w=e.w-t.w,this}multiply(e){return this.x*=e.x,this.y*=e.y,this.z*=e.z,this.w*=e.w,this}multiplyScalar(e){return this.x*=e,this.y*=e,this.z*=e,this.w*=e,this}applyMatrix4(e){let t=this.x,i=this.y,s=this.z,r=this.w,a=e.elements;return this.x=a[0]*t+a[4]*i+a[8]*s+a[12]*r,this.y=a[1]*t+a[5]*i+a[9]*s+a[13]*r,this.z=a[2]*t+a[6]*i+a[10]*s+a[14]*r,this.w=a[3]*t+a[7]*i+a[11]*s+a[15]*r,this}divide(e){return this.x/=e.x,this.y/=e.y,this.z/=e.z,this.w/=e.w,this}divideScalar(e){return this.multiplyScalar(1/e)}setAxisAngleFromQuaternion(e){this.w=2*Math.acos(e.w);let t=Math.sqrt(1-e.w*e.w);return t<1e-4?(this.x=1,this.y=0,this.z=0):(this.x=e.x/t,this.y=e.y/t,this.z=e.z/t),this}setAxisAngleFromRotationMatrix(e){let t,i,s,r,c=e.elements,l=c[0],u=c[4],h=c[8],d=c[1],f=c[5],g=c[9],x=c[2],m=c[6],p=c[10];if(Math.abs(u-d)<.01&&Math.abs(h-x)<.01&&Math.abs(g-m)<.01){if(Math.abs(u+d)<.1&&Math.abs(h+x)<.1&&Math.abs(g+m)<.1&&Math.abs(l+f+p-3)<.1)return this.set(1,0,0,0),this;t=Math.PI;let M=(l+1)/2,y=(f+1)/2,R=(p+1)/2,E=(u+d)/4,P=(h+x)/4,D=(g+m)/4;return M>y&&M>R?M<.01?(i=0,s=.707106781,r=.707106781):(i=Math.sqrt(M),s=E/i,r=P/i):y>R?y<.01?(i=.707106781,s=0,r=.707106781):(s=Math.sqrt(y),i=E/s,r=D/s):R<.01?(i=.707106781,s=.707106781,r=0):(r=Math.sqrt(R),i=P/r,s=D/r),this.set(i,s,r,t),this}let T=Math.sqrt((m-g)*(m-g)+(h-x)*(h-x)+(d-u)*(d-u));return Math.abs(T)<.001&&(T=1),this.x=(m-g)/T,this.y=(h-x)/T,this.z=(d-u)/T,this.w=Math.acos((l+f+p-1)/2),this}setFromMatrixPosition(e){let t=e.elements;return this.x=t[12],this.y=t[13],this.z=t[14],this.w=t[15],this}min(e){return this.x=Math.min(this.x,e.x),this.y=Math.min(this.y,e.y),this.z=Math.min(this.z,e.z),this.w=Math.min(this.w,e.w),this}max(e){return this.x=Math.max(this.x,e.x),this.y=Math.max(this.y,e.y),this.z=Math.max(this.z,e.z),this.w=Math.max(this.w,e.w),this}clamp(e,t){return this.x=Je(this.x,e.x,t.x),this.y=Je(this.y,e.y,t.y),this.z=Je(this.z,e.z,t.z),this.w=Je(this.w,e.w,t.w),this}clampScalar(e,t){return this.x=Je(this.x,e,t),this.y=Je(this.y,e,t),this.z=Je(this.z,e,t),this.w=Je(this.w,e,t),this}clampLength(e,t){let i=this.length();return this.divideScalar(i||1).multiplyScalar(Je(i,e,t))}floor(){return this.x=Math.floor(this.x),this.y=Math.floor(this.y),this.z=Math.floor(this.z),this.w=Math.floor(this.w),this}ceil(){return this.x=Math.ceil(this.x),this.y=Math.ceil(this.y),this.z=Math.ceil(this.z),this.w=Math.ceil(this.w),this}round(){return this.x=Math.round(this.x),this.y=Math.round(this.y),this.z=Math.round(this.z),this.w=Math.round(this.w),this}roundToZero(){return this.x=Math.trunc(this.x),this.y=Math.trunc(this.y),this.z=Math.trunc(this.z),this.w=Math.trunc(this.w),this}negate(){return this.x=-this.x,this.y=-this.y,this.z=-this.z,this.w=-this.w,this}dot(e){return this.x*e.x+this.y*e.y+this.z*e.z+this.w*e.w}lengthSq(){return this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w}length(){return Math.sqrt(this.x*this.x+this.y*this.y+this.z*this.z+this.w*this.w)}manhattanLength(){return Math.abs(this.x)+Math.abs(this.y)+Math.abs(this.z)+Math.abs(this.w)}normalize(){return this.divideScalar(this.length()||1)}setLength(e){return this.normalize().multiplyScalar(e)}lerp(e,t){return this.x+=(e.x-this.x)*t,this.y+=(e.y-this.y)*t,this.z+=(e.z-this.z)*t,this.w+=(e.w-this.w)*t,this}lerpVectors(e,t,i){return this.x=e.x+(t.x-e.x)*i,this.y=e.y+(t.y-e.y)*i,this.z=e.z+(t.z-e.z)*i,this.w=e.w+(t.w-e.w)*i,this}equals(e){return e.x===this.x&&e.y===this.y&&e.z===this.z&&e.w===this.w}fromArray(e,t=0){return this.x=e[t],this.y=e[t+1],this.z=e[t+2],this.w=e[t+3],this}toArray(e=[],t=0){return e[t]=this.x,e[t+1]=this.y,e[t+2]=this.z,e[t+3]=this.w,e}fromBufferAttribute(e,t){return this.x=e.getX(t),this.y=e.getY(t),this.z=e.getZ(t),this.w=e.getW(t),this}random(){return this.x=Math.random(),this.y=Math.random(),this.z=Math.random(),this.w=Math.random(),this}*[Symbol.iterator](){yield this.x,yield this.y,yield this.z,yield this.w}},_a=class extends Mn{constructor(e=1,t=1,i={}){super(),i=Object.assign({generateMipmaps:!1,internalFormat:null,minFilter:gn,depthBuffer:!0,stencilBuffer:!1,resolveDepthBuffer:!0,resolveStencilBuffer:!0,depthTexture:null,samples:0,count:1,depth:1,multiview:!1},i),this.isRenderTarget=!0,this.width=e,this.height=t,this.depth=i.depth,this.scissor=new wt(0,0,e,t),this.scissorTest=!1,this.viewport=new wt(0,0,e,t);let s={width:e,height:t,depth:i.depth},r=new Yt(s);this.textures=[];let a=i.count;for(let o=0;o<a;o++)this.textures[o]=r.clone(),this.textures[o].isRenderTargetTexture=!0,this.textures[o].renderTarget=this;this._setTextureOptions(i),this.depthBuffer=i.depthBuffer,this.stencilBuffer=i.stencilBuffer,this.resolveDepthBuffer=i.resolveDepthBuffer,this.resolveStencilBuffer=i.resolveStencilBuffer,this._depthTexture=null,this.depthTexture=i.depthTexture,this.samples=i.samples,this.multiview=i.multiview}_setTextureOptions(e={}){let t={minFilter:gn,generateMipmaps:!1,flipY:!1,internalFormat:null};e.mapping!==void 0&&(t.mapping=e.mapping),e.wrapS!==void 0&&(t.wrapS=e.wrapS),e.wrapT!==void 0&&(t.wrapT=e.wrapT),e.wrapR!==void 0&&(t.wrapR=e.wrapR),e.magFilter!==void 0&&(t.magFilter=e.magFilter),e.minFilter!==void 0&&(t.minFilter=e.minFilter),e.format!==void 0&&(t.format=e.format),e.type!==void 0&&(t.type=e.type),e.anisotropy!==void 0&&(t.anisotropy=e.anisotropy),e.colorSpace!==void 0&&(t.colorSpace=e.colorSpace),e.flipY!==void 0&&(t.flipY=e.flipY),e.generateMipmaps!==void 0&&(t.generateMipmaps=e.generateMipmaps),e.internalFormat!==void 0&&(t.internalFormat=e.internalFormat);for(let i=0;i<this.textures.length;i++)this.textures[i].setValues(t)}get texture(){return this.textures[0]}set texture(e){this.textures[0]=e}set depthTexture(e){this._depthTexture!==null&&(this._depthTexture.renderTarget=null),e!==null&&(e.renderTarget=this),this._depthTexture=e}get depthTexture(){return this._depthTexture}setSize(e,t,i=1){if(this.width!==e||this.height!==t||this.depth!==i){this.width=e,this.height=t,this.depth=i;for(let s=0,r=this.textures.length;s<r;s++)this.textures[s].image.width=e,this.textures[s].image.height=t,this.textures[s].image.depth=i,this.textures[s].isArrayTexture=this.textures[s].image.depth>1;this.dispose()}this.viewport.set(0,0,e,t),this.scissor.set(0,0,e,t)}clone(){return new this.constructor().copy(this)}copy(e){this.width=e.width,this.height=e.height,this.depth=e.depth,this.scissor.copy(e.scissor),this.scissorTest=e.scissorTest,this.viewport.copy(e.viewport),this.textures.length=0;for(let t=0,i=e.textures.length;t<i;t++){this.textures[t]=e.textures[t].clone(),this.textures[t].isRenderTargetTexture=!0,this.textures[t].renderTarget=this;let s=Object.assign({},e.textures[t].image);this.textures[t].source=new us(s)}return this.depthBuffer=e.depthBuffer,this.stencilBuffer=e.stencilBuffer,this.resolveDepthBuffer=e.resolveDepthBuffer,this.resolveStencilBuffer=e.resolveStencilBuffer,e.depthTexture!==null&&(this.depthTexture=e.depthTexture.clone()),this.samples=e.samples,this}dispose(){this.dispatchEvent({type:"dispose"})}},Sn=class extends _a{constructor(e=1,t=1,i={}){super(e,t,i),this.isWebGLRenderTarget=!0}},Js=class extends Yt{constructor(e=null,t=1,i=1,s=1){super(null),this.isDataArrayTexture=!0,this.image={data:e,width:t,height:i,depth:s},this.magFilter=on,this.minFilter=on,this.wrapR=si,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1,this.layerUpdates=new Set}addLayerUpdate(e){this.layerUpdates.add(e)}clearLayerUpdates(){this.layerUpdates.clear()}};var xa=class extends Yt{constructor(e=null,t=1,i=1,s=1){super(null),this.isData3DTexture=!0,this.image={data:e,width:t,height:i,depth:s},this.magFilter=on,this.minFilter=on,this.wrapR=si,this.generateMipmaps=!1,this.flipY=!1,this.unpackAlignment=1}};var Tn=class{constructor(e=new N(1/0,1/0,1/0),t=new N(-1/0,-1/0,-1/0)){this.isBox3=!0,this.min=e,this.max=t}set(e,t){return this.min.copy(e),this.max.copy(t),this}setFromArray(e){this.makeEmpty();for(let t=0,i=e.length;t<i;t+=3)this.expandByPoint(dn.fromArray(e,t));return this}setFromBufferAttribute(e){this.makeEmpty();for(let t=0,i=e.count;t<i;t++)this.expandByPoint(dn.fromBufferAttribute(e,t));return this}setFromPoints(e){this.makeEmpty();for(let t=0,i=e.length;t<i;t++)this.expandByPoint(e[t]);return this}setFromCenterAndSize(e,t){let i=dn.copy(t).multiplyScalar(.5);return this.min.copy(e).sub(i),this.max.copy(e).add(i),this}setFromObject(e,t=!1){return this.makeEmpty(),this.expandByObject(e,t)}clone(){return new this.constructor().copy(this)}copy(e){return this.min.copy(e.min),this.max.copy(e.max),this}makeEmpty(){return this.min.x=this.min.y=this.min.z=1/0,this.max.x=this.max.y=this.max.z=-1/0,this}isEmpty(){return this.max.x<this.min.x||this.max.y<this.min.y||this.max.z<this.min.z}getCenter(e){return this.isEmpty()?e.set(0,0,0):e.addVectors(this.min,this.max).multiplyScalar(.5)}getSize(e){return this.isEmpty()?e.set(0,0,0):e.subVectors(this.max,this.min)}expandByPoint(e){return this.min.min(e),this.max.max(e),this}expandByVector(e){return this.min.sub(e),this.max.add(e),this}expandByScalar(e){return this.min.addScalar(-e),this.max.addScalar(e),this}expandByObject(e,t=!1){e.updateWorldMatrix(!1,!1);let i=e.geometry;if(i!==void 0){let r=i.getAttribute("position");if(t===!0&&r!==void 0&&e.isInstancedMesh!==!0)for(let a=0,o=r.count;a<o;a++)e.isMesh===!0?e.getVertexPosition(a,dn):dn.fromBufferAttribute(r,a),dn.applyMatrix4(e.matrixWorld),this.expandByPoint(dn);else e.boundingBox!==void 0?(e.boundingBox===null&&e.computeBoundingBox(),Gr.copy(e.boundingBox)):(i.boundingBox===null&&i.computeBoundingBox(),Gr.copy(i.boundingBox)),Gr.applyMatrix4(e.matrixWorld),this.union(Gr)}let s=e.children;for(let r=0,a=s.length;r<a;r++)this.expandByObject(s[r],t);return this}containsPoint(e){return e.x>=this.min.x&&e.x<=this.max.x&&e.y>=this.min.y&&e.y<=this.max.y&&e.z>=this.min.z&&e.z<=this.max.z}containsBox(e){return this.min.x<=e.min.x&&e.max.x<=this.max.x&&this.min.y<=e.min.y&&e.max.y<=this.max.y&&this.min.z<=e.min.z&&e.max.z<=this.max.z}getParameter(e,t){return t.set((e.x-this.min.x)/(this.max.x-this.min.x),(e.y-this.min.y)/(this.max.y-this.min.y),(e.z-this.min.z)/(this.max.z-this.min.z))}intersectsBox(e){return e.max.x>=this.min.x&&e.min.x<=this.max.x&&e.max.y>=this.min.y&&e.min.y<=this.max.y&&e.max.z>=this.min.z&&e.min.z<=this.max.z}intersectsSphere(e){return this.clampPoint(e.center,dn),dn.distanceToSquared(e.center)<=e.radius*e.radius}intersectsPlane(e){let t,i;return e.normal.x>0?(t=e.normal.x*this.min.x,i=e.normal.x*this.max.x):(t=e.normal.x*this.max.x,i=e.normal.x*this.min.x),e.normal.y>0?(t+=e.normal.y*this.min.y,i+=e.normal.y*this.max.y):(t+=e.normal.y*this.max.y,i+=e.normal.y*this.min.y),e.normal.z>0?(t+=e.normal.z*this.min.z,i+=e.normal.z*this.max.z):(t+=e.normal.z*this.max.z,i+=e.normal.z*this.min.z),t<=-e.constant&&i>=-e.constant}intersectsTriangle(e){if(this.isEmpty())return!1;this.getCenter(Os),Wr.subVectors(this.max,Os),Zi.subVectors(e.a,Os),Ji.subVectors(e.b,Os),Ki.subVectors(e.c,Os),Kn.subVectors(Ji,Zi),jn.subVectors(Ki,Ji),yi.subVectors(Zi,Ki);let t=[0,-Kn.z,Kn.y,0,-jn.z,jn.y,0,-yi.z,yi.y,Kn.z,0,-Kn.x,jn.z,0,-jn.x,yi.z,0,-yi.x,-Kn.y,Kn.x,0,-jn.y,jn.x,0,-yi.y,yi.x,0];return!il(t,Zi,Ji,Ki,Wr)||(t=[1,0,0,0,1,0,0,0,1],!il(t,Zi,Ji,Ki,Wr))?!1:(Xr.crossVectors(Kn,jn),t=[Xr.x,Xr.y,Xr.z],il(t,Zi,Ji,Ki,Wr))}clampPoint(e,t){return t.copy(e).clamp(this.min,this.max)}distanceToPoint(e){return this.clampPoint(e,dn).distanceTo(e)}getBoundingSphere(e){return this.isEmpty()?e.makeEmpty():(this.getCenter(e.center),e.radius=this.getSize(dn).length()*.5),e}intersect(e){return this.min.max(e.min),this.max.min(e.max),this.isEmpty()&&this.makeEmpty(),this}union(e){return this.min.min(e.min),this.max.max(e.max),this}applyMatrix4(e){return this.isEmpty()?this:(On[0].set(this.min.x,this.min.y,this.min.z).applyMatrix4(e),On[1].set(this.min.x,this.min.y,this.max.z).applyMatrix4(e),On[2].set(this.min.x,this.max.y,this.min.z).applyMatrix4(e),On[3].set(this.min.x,this.max.y,this.max.z).applyMatrix4(e),On[4].set(this.max.x,this.min.y,this.min.z).applyMatrix4(e),On[5].set(this.max.x,this.min.y,this.max.z).applyMatrix4(e),On[6].set(this.max.x,this.max.y,this.min.z).applyMatrix4(e),On[7].set(this.max.x,this.max.y,this.max.z).applyMatrix4(e),this.setFromPoints(On),this)}translate(e){return this.min.add(e),this.max.add(e),this}equals(e){return e.min.equals(this.min)&&e.max.equals(this.max)}toJSON(){return{min:this.min.toArray(),max:this.max.toArray()}}fromJSON(e){return this.min.fromArray(e.min),this.max.fromArray(e.max),this}},On=[new N,new N,new N,new N,new N,new N,new N,new N],dn=new N,Gr=new Tn,Zi=new N,Ji=new N,Ki=new N,Kn=new N,jn=new N,yi=new N,Os=new N,Wr=new N,Xr=new N,wi=new N;function il(n,e,t,i,s){for(let r=0,a=n.length-3;r<=a;r+=3){wi.fromArray(n,r);let o=s.x*Math.abs(wi.x)+s.y*Math.abs(wi.y)+s.z*Math.abs(wi.z),c=e.dot(wi),l=t.dot(wi),u=i.dot(wi);if(Math.max(-Math.max(c,l,u),Math.min(c,l,u))>o)return!1}return!0}var Xf=new Tn,ks=new N,sl=new N,ds=class{constructor(e=new N,t=-1){this.isSphere=!0,this.center=e,this.radius=t}set(e,t){return this.center.copy(e),this.radius=t,this}setFromPoints(e,t){let i=this.center;t!==void 0?i.copy(t):Xf.setFromPoints(e).getCenter(i);let s=0;for(let r=0,a=e.length;r<a;r++)s=Math.max(s,i.distanceToSquared(e[r]));return this.radius=Math.sqrt(s),this}copy(e){return this.center.copy(e.center),this.radius=e.radius,this}isEmpty(){return this.radius<0}makeEmpty(){return this.center.set(0,0,0),this.radius=-1,this}containsPoint(e){return e.distanceToSquared(this.center)<=this.radius*this.radius}distanceToPoint(e){return e.distanceTo(this.center)-this.radius}intersectsSphere(e){let t=this.radius+e.radius;return e.center.distanceToSquared(this.center)<=t*t}intersectsBox(e){return e.intersectsSphere(this)}intersectsPlane(e){return Math.abs(e.distanceToPoint(this.center))<=this.radius}clampPoint(e,t){let i=this.center.distanceToSquared(e);return t.copy(e),i>this.radius*this.radius&&(t.sub(this.center).normalize(),t.multiplyScalar(this.radius).add(this.center)),t}getBoundingBox(e){return this.isEmpty()?(e.makeEmpty(),e):(e.set(this.center,this.center),e.expandByScalar(this.radius),e)}applyMatrix4(e){return this.center.applyMatrix4(e),this.radius=this.radius*e.getMaxScaleOnAxis(),this}translate(e){return this.center.add(e),this}expandByPoint(e){if(this.isEmpty())return this.center.copy(e),this.radius=0,this;ks.subVectors(e,this.center);let t=ks.lengthSq();if(t>this.radius*this.radius){let i=Math.sqrt(t),s=(i-this.radius)*.5;this.center.addScaledVector(ks,s/i),this.radius+=s}return this}union(e){return e.isEmpty()?this:this.isEmpty()?(this.copy(e),this):(this.center.equals(e.center)===!0?this.radius=Math.max(this.radius,e.radius):(sl.subVectors(e.center,this.center).setLength(e.radius),this.expandByPoint(ks.copy(e.center).add(sl)),this.expandByPoint(ks.copy(e.center).sub(sl))),this)}equals(e){return e.center.equals(this.center)&&e.radius===this.radius}clone(){return new this.constructor().copy(this)}toJSON(){return{radius:this.radius,center:this.center.toArray()}}fromJSON(e){return this.radius=e.radius,this.center.fromArray(e.center),this}},kn=new N,rl=new N,qr=new N,Qn=new N,al=new N,Yr=new N,ol=new N,fs=class{constructor(e=new N,t=new N(0,0,-1)){this.origin=e,this.direction=t}set(e,t){return this.origin.copy(e),this.direction.copy(t),this}copy(e){return this.origin.copy(e.origin),this.direction.copy(e.direction),this}at(e,t){return t.copy(this.origin).addScaledVector(this.direction,e)}lookAt(e){return this.direction.copy(e).sub(this.origin).normalize(),this}recast(e){return this.origin.copy(this.at(e,kn)),this}closestPointToPoint(e,t){t.subVectors(e,this.origin);let i=t.dot(this.direction);return i<0?t.copy(this.origin):t.copy(this.origin).addScaledVector(this.direction,i)}distanceToPoint(e){return Math.sqrt(this.distanceSqToPoint(e))}distanceSqToPoint(e){let t=kn.subVectors(e,this.origin).dot(this.direction);return t<0?this.origin.distanceToSquared(e):(kn.copy(this.origin).addScaledVector(this.direction,t),kn.distanceToSquared(e))}distanceSqToSegment(e,t,i,s){rl.copy(e).add(t).multiplyScalar(.5),qr.copy(t).sub(e).normalize(),Qn.copy(this.origin).sub(rl);let r=e.distanceTo(t)*.5,a=-this.direction.dot(qr),o=Qn.dot(this.direction),c=-Qn.dot(qr),l=Qn.lengthSq(),u=Math.abs(1-a*a),h,d,f,g;if(u>0)if(h=a*c-o,d=a*o-c,g=r*u,h>=0)if(d>=-g)if(d<=g){let x=1/u;h*=x,d*=x,f=h*(h+a*d+2*o)+d*(a*h+d+2*c)+l}else d=r,h=Math.max(0,-(a*d+o)),f=-h*h+d*(d+2*c)+l;else d=-r,h=Math.max(0,-(a*d+o)),f=-h*h+d*(d+2*c)+l;else d<=-g?(h=Math.max(0,-(-a*r+o)),d=h>0?-r:Math.min(Math.max(-r,-c),r),f=-h*h+d*(d+2*c)+l):d<=g?(h=0,d=Math.min(Math.max(-r,-c),r),f=d*(d+2*c)+l):(h=Math.max(0,-(a*r+o)),d=h>0?r:Math.min(Math.max(-r,-c),r),f=-h*h+d*(d+2*c)+l);else d=a>0?-r:r,h=Math.max(0,-(a*d+o)),f=-h*h+d*(d+2*c)+l;return i&&i.copy(this.origin).addScaledVector(this.direction,h),s&&s.copy(rl).addScaledVector(qr,d),f}intersectSphere(e,t){kn.subVectors(e.center,this.origin);let i=kn.dot(this.direction),s=kn.dot(kn)-i*i,r=e.radius*e.radius;if(s>r)return null;let a=Math.sqrt(r-s),o=i-a,c=i+a;return c<0?null:o<0?this.at(c,t):this.at(o,t)}intersectsSphere(e){return e.radius<0?!1:this.distanceSqToPoint(e.center)<=e.radius*e.radius}distanceToPlane(e){let t=e.normal.dot(this.direction);if(t===0)return e.distanceToPoint(this.origin)===0?0:null;let i=-(this.origin.dot(e.normal)+e.constant)/t;return i>=0?i:null}intersectPlane(e,t){let i=this.distanceToPlane(e);return i===null?null:this.at(i,t)}intersectsPlane(e){let t=e.distanceToPoint(this.origin);return t===0||e.normal.dot(this.direction)*t<0}intersectBox(e,t){let i,s,r,a,o,c,l=1/this.direction.x,u=1/this.direction.y,h=1/this.direction.z,d=this.origin;return l>=0?(i=(e.min.x-d.x)*l,s=(e.max.x-d.x)*l):(i=(e.max.x-d.x)*l,s=(e.min.x-d.x)*l),u>=0?(r=(e.min.y-d.y)*u,a=(e.max.y-d.y)*u):(r=(e.max.y-d.y)*u,a=(e.min.y-d.y)*u),i>a||r>s||((r>i||isNaN(i))&&(i=r),(a<s||isNaN(s))&&(s=a),h>=0?(o=(e.min.z-d.z)*h,c=(e.max.z-d.z)*h):(o=(e.max.z-d.z)*h,c=(e.min.z-d.z)*h),i>c||o>s)||((o>i||i!==i)&&(i=o),(c<s||s!==s)&&(s=c),s<0)?null:this.at(i>=0?i:s,t)}intersectsBox(e){return this.intersectBox(e,kn)!==null}intersectTriangle(e,t,i,s,r){al.subVectors(t,e),Yr.subVectors(i,e),ol.crossVectors(al,Yr);let a=this.direction.dot(ol),o;if(a>0){if(s)return null;o=1}else if(a<0)o=-1,a=-a;else return null;Qn.subVectors(this.origin,e);let c=o*this.direction.dot(Yr.crossVectors(Qn,Yr));if(c<0)return null;let l=o*this.direction.dot(al.cross(Qn));if(l<0||c+l>a)return null;let u=-o*Qn.dot(ol);return u<0?null:this.at(u/a,r)}applyMatrix4(e){return this.origin.applyMatrix4(e),this.direction.transformDirection(e),this}equals(e){return e.origin.equals(this.origin)&&e.direction.equals(this.direction)}clone(){return new this.constructor().copy(this)}},Mt=class n{constructor(e,t,i,s,r,a,o,c,l,u,h,d,f,g,x,m){n.prototype.isMatrix4=!0,this.elements=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],e!==void 0&&this.set(e,t,i,s,r,a,o,c,l,u,h,d,f,g,x,m)}set(e,t,i,s,r,a,o,c,l,u,h,d,f,g,x,m){let p=this.elements;return p[0]=e,p[4]=t,p[8]=i,p[12]=s,p[1]=r,p[5]=a,p[9]=o,p[13]=c,p[2]=l,p[6]=u,p[10]=h,p[14]=d,p[3]=f,p[7]=g,p[11]=x,p[15]=m,this}identity(){return this.set(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1),this}clone(){return new n().fromArray(this.elements)}copy(e){let t=this.elements,i=e.elements;return t[0]=i[0],t[1]=i[1],t[2]=i[2],t[3]=i[3],t[4]=i[4],t[5]=i[5],t[6]=i[6],t[7]=i[7],t[8]=i[8],t[9]=i[9],t[10]=i[10],t[11]=i[11],t[12]=i[12],t[13]=i[13],t[14]=i[14],t[15]=i[15],this}copyPosition(e){let t=this.elements,i=e.elements;return t[12]=i[12],t[13]=i[13],t[14]=i[14],this}setFromMatrix3(e){let t=e.elements;return this.set(t[0],t[3],t[6],0,t[1],t[4],t[7],0,t[2],t[5],t[8],0,0,0,0,1),this}extractBasis(e,t,i){return e.setFromMatrixColumn(this,0),t.setFromMatrixColumn(this,1),i.setFromMatrixColumn(this,2),this}makeBasis(e,t,i){return this.set(e.x,t.x,i.x,0,e.y,t.y,i.y,0,e.z,t.z,i.z,0,0,0,0,1),this}extractRotation(e){let t=this.elements,i=e.elements,s=1/ji.setFromMatrixColumn(e,0).length(),r=1/ji.setFromMatrixColumn(e,1).length(),a=1/ji.setFromMatrixColumn(e,2).length();return t[0]=i[0]*s,t[1]=i[1]*s,t[2]=i[2]*s,t[3]=0,t[4]=i[4]*r,t[5]=i[5]*r,t[6]=i[6]*r,t[7]=0,t[8]=i[8]*a,t[9]=i[9]*a,t[10]=i[10]*a,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromEuler(e){let t=this.elements,i=e.x,s=e.y,r=e.z,a=Math.cos(i),o=Math.sin(i),c=Math.cos(s),l=Math.sin(s),u=Math.cos(r),h=Math.sin(r);if(e.order==="XYZ"){let d=a*u,f=a*h,g=o*u,x=o*h;t[0]=c*u,t[4]=-c*h,t[8]=l,t[1]=f+g*l,t[5]=d-x*l,t[9]=-o*c,t[2]=x-d*l,t[6]=g+f*l,t[10]=a*c}else if(e.order==="YXZ"){let d=c*u,f=c*h,g=l*u,x=l*h;t[0]=d+x*o,t[4]=g*o-f,t[8]=a*l,t[1]=a*h,t[5]=a*u,t[9]=-o,t[2]=f*o-g,t[6]=x+d*o,t[10]=a*c}else if(e.order==="ZXY"){let d=c*u,f=c*h,g=l*u,x=l*h;t[0]=d-x*o,t[4]=-a*h,t[8]=g+f*o,t[1]=f+g*o,t[5]=a*u,t[9]=x-d*o,t[2]=-a*l,t[6]=o,t[10]=a*c}else if(e.order==="ZYX"){let d=a*u,f=a*h,g=o*u,x=o*h;t[0]=c*u,t[4]=g*l-f,t[8]=d*l+x,t[1]=c*h,t[5]=x*l+d,t[9]=f*l-g,t[2]=-l,t[6]=o*c,t[10]=a*c}else if(e.order==="YZX"){let d=a*c,f=a*l,g=o*c,x=o*l;t[0]=c*u,t[4]=x-d*h,t[8]=g*h+f,t[1]=h,t[5]=a*u,t[9]=-o*u,t[2]=-l*u,t[6]=f*h+g,t[10]=d-x*h}else if(e.order==="XZY"){let d=a*c,f=a*l,g=o*c,x=o*l;t[0]=c*u,t[4]=-h,t[8]=l*u,t[1]=d*h+x,t[5]=a*u,t[9]=f*h-g,t[2]=g*h-f,t[6]=o*u,t[10]=x*h+d}return t[3]=0,t[7]=0,t[11]=0,t[12]=0,t[13]=0,t[14]=0,t[15]=1,this}makeRotationFromQuaternion(e){return this.compose(qf,e,Yf)}lookAt(e,t,i){let s=this.elements;return jt.subVectors(e,t),jt.lengthSq()===0&&(jt.z=1),jt.normalize(),ei.crossVectors(i,jt),ei.lengthSq()===0&&(Math.abs(i.z)===1?jt.x+=1e-4:jt.z+=1e-4,jt.normalize(),ei.crossVectors(i,jt)),ei.normalize(),$r.crossVectors(jt,ei),s[0]=ei.x,s[4]=$r.x,s[8]=jt.x,s[1]=ei.y,s[5]=$r.y,s[9]=jt.y,s[2]=ei.z,s[6]=$r.z,s[10]=jt.z,this}multiply(e){return this.multiplyMatrices(this,e)}premultiply(e){return this.multiplyMatrices(e,this)}multiplyMatrices(e,t){let i=e.elements,s=t.elements,r=this.elements,a=i[0],o=i[4],c=i[8],l=i[12],u=i[1],h=i[5],d=i[9],f=i[13],g=i[2],x=i[6],m=i[10],p=i[14],T=i[3],M=i[7],y=i[11],R=i[15],E=s[0],P=s[4],D=s[8],b=s[12],w=s[1],C=s[5],k=s[9],G=s[13],q=s[2],X=s[6],V=s[10],te=s[14],U=s[3],Q=s[7],he=s[11],ue=s[15];return r[0]=a*E+o*w+c*q+l*U,r[4]=a*P+o*C+c*X+l*Q,r[8]=a*D+o*k+c*V+l*he,r[12]=a*b+o*G+c*te+l*ue,r[1]=u*E+h*w+d*q+f*U,r[5]=u*P+h*C+d*X+f*Q,r[9]=u*D+h*k+d*V+f*he,r[13]=u*b+h*G+d*te+f*ue,r[2]=g*E+x*w+m*q+p*U,r[6]=g*P+x*C+m*X+p*Q,r[10]=g*D+x*k+m*V+p*he,r[14]=g*b+x*G+m*te+p*ue,r[3]=T*E+M*w+y*q+R*U,r[7]=T*P+M*C+y*X+R*Q,r[11]=T*D+M*k+y*V+R*he,r[15]=T*b+M*G+y*te+R*ue,this}multiplyScalar(e){let t=this.elements;return t[0]*=e,t[4]*=e,t[8]*=e,t[12]*=e,t[1]*=e,t[5]*=e,t[9]*=e,t[13]*=e,t[2]*=e,t[6]*=e,t[10]*=e,t[14]*=e,t[3]*=e,t[7]*=e,t[11]*=e,t[15]*=e,this}determinant(){let e=this.elements,t=e[0],i=e[4],s=e[8],r=e[12],a=e[1],o=e[5],c=e[9],l=e[13],u=e[2],h=e[6],d=e[10],f=e[14],g=e[3],x=e[7],m=e[11],p=e[15];return g*(+r*c*h-s*l*h-r*o*d+i*l*d+s*o*f-i*c*f)+x*(+t*c*f-t*l*d+r*a*d-s*a*f+s*l*u-r*c*u)+m*(+t*l*h-t*o*f-r*a*h+i*a*f+r*o*u-i*l*u)+p*(-s*o*u-t*c*h+t*o*d+s*a*h-i*a*d+i*c*u)}transpose(){let e=this.elements,t;return t=e[1],e[1]=e[4],e[4]=t,t=e[2],e[2]=e[8],e[8]=t,t=e[6],e[6]=e[9],e[9]=t,t=e[3],e[3]=e[12],e[12]=t,t=e[7],e[7]=e[13],e[13]=t,t=e[11],e[11]=e[14],e[14]=t,this}setPosition(e,t,i){let s=this.elements;return e.isVector3?(s[12]=e.x,s[13]=e.y,s[14]=e.z):(s[12]=e,s[13]=t,s[14]=i),this}invert(){let e=this.elements,t=e[0],i=e[1],s=e[2],r=e[3],a=e[4],o=e[5],c=e[6],l=e[7],u=e[8],h=e[9],d=e[10],f=e[11],g=e[12],x=e[13],m=e[14],p=e[15],T=h*m*l-x*d*l+x*c*f-o*m*f-h*c*p+o*d*p,M=g*d*l-u*m*l-g*c*f+a*m*f+u*c*p-a*d*p,y=u*x*l-g*h*l+g*o*f-a*x*f-u*o*p+a*h*p,R=g*h*c-u*x*c-g*o*d+a*x*d+u*o*m-a*h*m,E=t*T+i*M+s*y+r*R;if(E===0)return this.set(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0);let P=1/E;return e[0]=T*P,e[1]=(x*d*r-h*m*r-x*s*f+i*m*f+h*s*p-i*d*p)*P,e[2]=(o*m*r-x*c*r+x*s*l-i*m*l-o*s*p+i*c*p)*P,e[3]=(h*c*r-o*d*r-h*s*l+i*d*l+o*s*f-i*c*f)*P,e[4]=M*P,e[5]=(u*m*r-g*d*r+g*s*f-t*m*f-u*s*p+t*d*p)*P,e[6]=(g*c*r-a*m*r-g*s*l+t*m*l+a*s*p-t*c*p)*P,e[7]=(a*d*r-u*c*r+u*s*l-t*d*l-a*s*f+t*c*f)*P,e[8]=y*P,e[9]=(g*h*r-u*x*r-g*i*f+t*x*f+u*i*p-t*h*p)*P,e[10]=(a*x*r-g*o*r+g*i*l-t*x*l-a*i*p+t*o*p)*P,e[11]=(u*o*r-a*h*r-u*i*l+t*h*l+a*i*f-t*o*f)*P,e[12]=R*P,e[13]=(u*x*s-g*h*s+g*i*d-t*x*d-u*i*m+t*h*m)*P,e[14]=(g*o*s-a*x*s-g*i*c+t*x*c+a*i*m-t*o*m)*P,e[15]=(a*h*s-u*o*s+u*i*c-t*h*c-a*i*d+t*o*d)*P,this}scale(e){let t=this.elements,i=e.x,s=e.y,r=e.z;return t[0]*=i,t[4]*=s,t[8]*=r,t[1]*=i,t[5]*=s,t[9]*=r,t[2]*=i,t[6]*=s,t[10]*=r,t[3]*=i,t[7]*=s,t[11]*=r,this}getMaxScaleOnAxis(){let e=this.elements,t=e[0]*e[0]+e[1]*e[1]+e[2]*e[2],i=e[4]*e[4]+e[5]*e[5]+e[6]*e[6],s=e[8]*e[8]+e[9]*e[9]+e[10]*e[10];return Math.sqrt(Math.max(t,i,s))}makeTranslation(e,t,i){return e.isVector3?this.set(1,0,0,e.x,0,1,0,e.y,0,0,1,e.z,0,0,0,1):this.set(1,0,0,e,0,1,0,t,0,0,1,i,0,0,0,1),this}makeRotationX(e){let t=Math.cos(e),i=Math.sin(e);return this.set(1,0,0,0,0,t,-i,0,0,i,t,0,0,0,0,1),this}makeRotationY(e){let t=Math.cos(e),i=Math.sin(e);return this.set(t,0,i,0,0,1,0,0,-i,0,t,0,0,0,0,1),this}makeRotationZ(e){let t=Math.cos(e),i=Math.sin(e);return this.set(t,-i,0,0,i,t,0,0,0,0,1,0,0,0,0,1),this}makeRotationAxis(e,t){let i=Math.cos(t),s=Math.sin(t),r=1-i,a=e.x,o=e.y,c=e.z,l=r*a,u=r*o;return this.set(l*a+i,l*o-s*c,l*c+s*o,0,l*o+s*c,u*o+i,u*c-s*a,0,l*c-s*o,u*c+s*a,r*c*c+i,0,0,0,0,1),this}makeScale(e,t,i){return this.set(e,0,0,0,0,t,0,0,0,0,i,0,0,0,0,1),this}makeShear(e,t,i,s,r,a){return this.set(1,i,r,0,e,1,a,0,t,s,1,0,0,0,0,1),this}compose(e,t,i){let s=this.elements,r=t._x,a=t._y,o=t._z,c=t._w,l=r+r,u=a+a,h=o+o,d=r*l,f=r*u,g=r*h,x=a*u,m=a*h,p=o*h,T=c*l,M=c*u,y=c*h,R=i.x,E=i.y,P=i.z;return s[0]=(1-(x+p))*R,s[1]=(f+y)*R,s[2]=(g-M)*R,s[3]=0,s[4]=(f-y)*E,s[5]=(1-(d+p))*E,s[6]=(m+T)*E,s[7]=0,s[8]=(g+M)*P,s[9]=(m-T)*P,s[10]=(1-(d+x))*P,s[11]=0,s[12]=e.x,s[13]=e.y,s[14]=e.z,s[15]=1,this}decompose(e,t,i){let s=this.elements,r=ji.set(s[0],s[1],s[2]).length(),a=ji.set(s[4],s[5],s[6]).length(),o=ji.set(s[8],s[9],s[10]).length();this.determinant()<0&&(r=-r),e.x=s[12],e.y=s[13],e.z=s[14],fn.copy(this);let l=1/r,u=1/a,h=1/o;return fn.elements[0]*=l,fn.elements[1]*=l,fn.elements[2]*=l,fn.elements[4]*=u,fn.elements[5]*=u,fn.elements[6]*=u,fn.elements[8]*=h,fn.elements[9]*=h,fn.elements[10]*=h,t.setFromRotationMatrix(fn),i.x=r,i.y=a,i.z=o,this}makePerspective(e,t,i,s,r,a,o=mn,c=!1){let l=this.elements,u=2*r/(t-e),h=2*r/(i-s),d=(t+e)/(t-e),f=(i+s)/(i-s),g,x;if(c)g=r/(a-r),x=a*r/(a-r);else if(o===mn)g=-(a+r)/(a-r),x=-2*a*r/(a-r);else if(o===$s)g=-a/(a-r),x=-a*r/(a-r);else throw new Error("THREE.Matrix4.makePerspective(): Invalid coordinate system: "+o);return l[0]=u,l[4]=0,l[8]=d,l[12]=0,l[1]=0,l[5]=h,l[9]=f,l[13]=0,l[2]=0,l[6]=0,l[10]=g,l[14]=x,l[3]=0,l[7]=0,l[11]=-1,l[15]=0,this}makeOrthographic(e,t,i,s,r,a,o=mn,c=!1){let l=this.elements,u=2/(t-e),h=2/(i-s),d=-(t+e)/(t-e),f=-(i+s)/(i-s),g,x;if(c)g=1/(a-r),x=a/(a-r);else if(o===mn)g=-2/(a-r),x=-(a+r)/(a-r);else if(o===$s)g=-1/(a-r),x=-r/(a-r);else throw new Error("THREE.Matrix4.makeOrthographic(): Invalid coordinate system: "+o);return l[0]=u,l[4]=0,l[8]=0,l[12]=d,l[1]=0,l[5]=h,l[9]=0,l[13]=f,l[2]=0,l[6]=0,l[10]=g,l[14]=x,l[3]=0,l[7]=0,l[11]=0,l[15]=1,this}equals(e){let t=this.elements,i=e.elements;for(let s=0;s<16;s++)if(t[s]!==i[s])return!1;return!0}fromArray(e,t=0){for(let i=0;i<16;i++)this.elements[i]=e[i+t];return this}toArray(e=[],t=0){let i=this.elements;return e[t]=i[0],e[t+1]=i[1],e[t+2]=i[2],e[t+3]=i[3],e[t+4]=i[4],e[t+5]=i[5],e[t+6]=i[6],e[t+7]=i[7],e[t+8]=i[8],e[t+9]=i[9],e[t+10]=i[10],e[t+11]=i[11],e[t+12]=i[12],e[t+13]=i[13],e[t+14]=i[14],e[t+15]=i[15],e}},ji=new N,fn=new Mt,qf=new N(0,0,0),Yf=new N(1,1,1),ei=new N,$r=new N,jt=new N,Ch=new Mt,Rh=new ln,_n=class n{constructor(e=0,t=0,i=0,s=n.DEFAULT_ORDER){this.isEuler=!0,this._x=e,this._y=t,this._z=i,this._order=s}get x(){return this._x}set x(e){this._x=e,this._onChangeCallback()}get y(){return this._y}set y(e){this._y=e,this._onChangeCallback()}get z(){return this._z}set z(e){this._z=e,this._onChangeCallback()}get order(){return this._order}set order(e){this._order=e,this._onChangeCallback()}set(e,t,i,s=this._order){return this._x=e,this._y=t,this._z=i,this._order=s,this._onChangeCallback(),this}clone(){return new this.constructor(this._x,this._y,this._z,this._order)}copy(e){return this._x=e._x,this._y=e._y,this._z=e._z,this._order=e._order,this._onChangeCallback(),this}setFromRotationMatrix(e,t=this._order,i=!0){let s=e.elements,r=s[0],a=s[4],o=s[8],c=s[1],l=s[5],u=s[9],h=s[2],d=s[6],f=s[10];switch(t){case"XYZ":this._y=Math.asin(Je(o,-1,1)),Math.abs(o)<.9999999?(this._x=Math.atan2(-u,f),this._z=Math.atan2(-a,r)):(this._x=Math.atan2(d,l),this._z=0);break;case"YXZ":this._x=Math.asin(-Je(u,-1,1)),Math.abs(u)<.9999999?(this._y=Math.atan2(o,f),this._z=Math.atan2(c,l)):(this._y=Math.atan2(-h,r),this._z=0);break;case"ZXY":this._x=Math.asin(Je(d,-1,1)),Math.abs(d)<.9999999?(this._y=Math.atan2(-h,f),this._z=Math.atan2(-a,l)):(this._y=0,this._z=Math.atan2(c,r));break;case"ZYX":this._y=Math.asin(-Je(h,-1,1)),Math.abs(h)<.9999999?(this._x=Math.atan2(d,f),this._z=Math.atan2(c,r)):(this._x=0,this._z=Math.atan2(-a,l));break;case"YZX":this._z=Math.asin(Je(c,-1,1)),Math.abs(c)<.9999999?(this._x=Math.atan2(-u,l),this._y=Math.atan2(-h,r)):(this._x=0,this._y=Math.atan2(o,f));break;case"XZY":this._z=Math.asin(-Je(a,-1,1)),Math.abs(a)<.9999999?(this._x=Math.atan2(d,l),this._y=Math.atan2(o,r)):(this._x=Math.atan2(-u,f),this._y=0);break;default:console.warn("THREE.Euler: .setFromRotationMatrix() encountered an unknown order: "+t)}return this._order=t,i===!0&&this._onChangeCallback(),this}setFromQuaternion(e,t,i){return Ch.makeRotationFromQuaternion(e),this.setFromRotationMatrix(Ch,t,i)}setFromVector3(e,t=this._order){return this.set(e.x,e.y,e.z,t)}reorder(e){return Rh.setFromEuler(this),this.setFromQuaternion(Rh,e)}equals(e){return e._x===this._x&&e._y===this._y&&e._z===this._z&&e._order===this._order}fromArray(e){return this._x=e[0],this._y=e[1],this._z=e[2],e[3]!==void 0&&(this._order=e[3]),this._onChangeCallback(),this}toArray(e=[],t=0){return e[t]=this._x,e[t+1]=this._y,e[t+2]=this._z,e[t+3]=this._order,e}_onChange(e){return this._onChangeCallback=e,this}_onChangeCallback(){}*[Symbol.iterator](){yield this._x,yield this._y,yield this._z,yield this._order}};_n.DEFAULT_ORDER="XYZ";var Ks=class{constructor(){this.mask=1}set(e){this.mask=(1<<e|0)>>>0}enable(e){this.mask|=1<<e|0}enableAll(){this.mask=-1}toggle(e){this.mask^=1<<e|0}disable(e){this.mask&=~(1<<e|0)}disableAll(){this.mask=0}test(e){return(this.mask&e.mask)!==0}isEnabled(e){return(this.mask&(1<<e|0))!==0}},$f=0,Ph=new N,Qi=new ln,Bn=new Mt,Zr=new N,Bs=new N,Zf=new N,Jf=new ln,Ih=new N(1,0,0),Nh=new N(0,1,0),Dh=new N(0,0,1),Lh={type:"added"},Kf={type:"removed"},es={type:"childadded",child:null},ll={type:"childremoved",child:null},Ft=class n extends Mn{constructor(){super(),this.isObject3D=!0,Object.defineProperty(this,"id",{value:$f++}),this.uuid=Fi(),this.name="",this.type="Object3D",this.parent=null,this.children=[],this.up=n.DEFAULT_UP.clone();let e=new N,t=new _n,i=new ln,s=new N(1,1,1);function r(){i.setFromEuler(t,!1)}function a(){t.setFromQuaternion(i,void 0,!1)}t._onChange(r),i._onChange(a),Object.defineProperties(this,{position:{configurable:!0,enumerable:!0,value:e},rotation:{configurable:!0,enumerable:!0,value:t},quaternion:{configurable:!0,enumerable:!0,value:i},scale:{configurable:!0,enumerable:!0,value:s},modelViewMatrix:{value:new Mt},normalMatrix:{value:new $e}}),this.matrix=new Mt,this.matrixWorld=new Mt,this.matrixAutoUpdate=n.DEFAULT_MATRIX_AUTO_UPDATE,this.matrixWorldAutoUpdate=n.DEFAULT_MATRIX_WORLD_AUTO_UPDATE,this.matrixWorldNeedsUpdate=!1,this.layers=new Ks,this.visible=!0,this.castShadow=!1,this.receiveShadow=!1,this.frustumCulled=!0,this.renderOrder=0,this.animations=[],this.customDepthMaterial=void 0,this.customDistanceMaterial=void 0,this.userData={}}onBeforeShadow(){}onAfterShadow(){}onBeforeRender(){}onAfterRender(){}applyMatrix4(e){this.matrixAutoUpdate&&this.updateMatrix(),this.matrix.premultiply(e),this.matrix.decompose(this.position,this.quaternion,this.scale)}applyQuaternion(e){return this.quaternion.premultiply(e),this}setRotationFromAxisAngle(e,t){this.quaternion.setFromAxisAngle(e,t)}setRotationFromEuler(e){this.quaternion.setFromEuler(e,!0)}setRotationFromMatrix(e){this.quaternion.setFromRotationMatrix(e)}setRotationFromQuaternion(e){this.quaternion.copy(e)}rotateOnAxis(e,t){return Qi.setFromAxisAngle(e,t),this.quaternion.multiply(Qi),this}rotateOnWorldAxis(e,t){return Qi.setFromAxisAngle(e,t),this.quaternion.premultiply(Qi),this}rotateX(e){return this.rotateOnAxis(Ih,e)}rotateY(e){return this.rotateOnAxis(Nh,e)}rotateZ(e){return this.rotateOnAxis(Dh,e)}translateOnAxis(e,t){return Ph.copy(e).applyQuaternion(this.quaternion),this.position.add(Ph.multiplyScalar(t)),this}translateX(e){return this.translateOnAxis(Ih,e)}translateY(e){return this.translateOnAxis(Nh,e)}translateZ(e){return this.translateOnAxis(Dh,e)}localToWorld(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(this.matrixWorld)}worldToLocal(e){return this.updateWorldMatrix(!0,!1),e.applyMatrix4(Bn.copy(this.matrixWorld).invert())}lookAt(e,t,i){e.isVector3?Zr.copy(e):Zr.set(e,t,i);let s=this.parent;this.updateWorldMatrix(!0,!1),Bs.setFromMatrixPosition(this.matrixWorld),this.isCamera||this.isLight?Bn.lookAt(Bs,Zr,this.up):Bn.lookAt(Zr,Bs,this.up),this.quaternion.setFromRotationMatrix(Bn),s&&(Bn.extractRotation(s.matrixWorld),Qi.setFromRotationMatrix(Bn),this.quaternion.premultiply(Qi.invert()))}add(e){if(arguments.length>1){for(let t=0;t<arguments.length;t++)this.add(arguments[t]);return this}return e===this?(console.error("THREE.Object3D.add: object can't be added as a child of itself.",e),this):(e&&e.isObject3D?(e.removeFromParent(),e.parent=this,this.children.push(e),e.dispatchEvent(Lh),es.child=e,this.dispatchEvent(es),es.child=null):console.error("THREE.Object3D.add: object not an instance of THREE.Object3D.",e),this)}remove(e){if(arguments.length>1){for(let i=0;i<arguments.length;i++)this.remove(arguments[i]);return this}let t=this.children.indexOf(e);return t!==-1&&(e.parent=null,this.children.splice(t,1),e.dispatchEvent(Kf),ll.child=e,this.dispatchEvent(ll),ll.child=null),this}removeFromParent(){let e=this.parent;return e!==null&&e.remove(this),this}clear(){return this.remove(...this.children)}attach(e){return this.updateWorldMatrix(!0,!1),Bn.copy(this.matrixWorld).invert(),e.parent!==null&&(e.parent.updateWorldMatrix(!0,!1),Bn.multiply(e.parent.matrixWorld)),e.applyMatrix4(Bn),e.removeFromParent(),e.parent=this,this.children.push(e),e.updateWorldMatrix(!1,!0),e.dispatchEvent(Lh),es.child=e,this.dispatchEvent(es),es.child=null,this}getObjectById(e){return this.getObjectByProperty("id",e)}getObjectByName(e){return this.getObjectByProperty("name",e)}getObjectByProperty(e,t){if(this[e]===t)return this;for(let i=0,s=this.children.length;i<s;i++){let a=this.children[i].getObjectByProperty(e,t);if(a!==void 0)return a}}getObjectsByProperty(e,t,i=[]){this[e]===t&&i.push(this);let s=this.children;for(let r=0,a=s.length;r<a;r++)s[r].getObjectsByProperty(e,t,i);return i}getWorldPosition(e){return this.updateWorldMatrix(!0,!1),e.setFromMatrixPosition(this.matrixWorld)}getWorldQuaternion(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Bs,e,Zf),e}getWorldScale(e){return this.updateWorldMatrix(!0,!1),this.matrixWorld.decompose(Bs,Jf,e),e}getWorldDirection(e){this.updateWorldMatrix(!0,!1);let t=this.matrixWorld.elements;return e.set(t[8],t[9],t[10]).normalize()}raycast(){}traverse(e){e(this);let t=this.children;for(let i=0,s=t.length;i<s;i++)t[i].traverse(e)}traverseVisible(e){if(this.visible===!1)return;e(this);let t=this.children;for(let i=0,s=t.length;i<s;i++)t[i].traverseVisible(e)}traverseAncestors(e){let t=this.parent;t!==null&&(e(t),t.traverseAncestors(e))}updateMatrix(){this.matrix.compose(this.position,this.quaternion,this.scale),this.matrixWorldNeedsUpdate=!0}updateMatrixWorld(e){this.matrixAutoUpdate&&this.updateMatrix(),(this.matrixWorldNeedsUpdate||e)&&(this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),this.matrixWorldNeedsUpdate=!1,e=!0);let t=this.children;for(let i=0,s=t.length;i<s;i++)t[i].updateMatrixWorld(e)}updateWorldMatrix(e,t){let i=this.parent;if(e===!0&&i!==null&&i.updateWorldMatrix(!0,!1),this.matrixAutoUpdate&&this.updateMatrix(),this.matrixWorldAutoUpdate===!0&&(this.parent===null?this.matrixWorld.copy(this.matrix):this.matrixWorld.multiplyMatrices(this.parent.matrixWorld,this.matrix)),t===!0){let s=this.children;for(let r=0,a=s.length;r<a;r++)s[r].updateWorldMatrix(!1,!0)}}toJSON(e){let t=e===void 0||typeof e=="string",i={};t&&(e={geometries:{},materials:{},textures:{},images:{},shapes:{},skeletons:{},animations:{},nodes:{}},i.metadata={version:4.7,type:"Object",generator:"Object3D.toJSON"});let s={};s.uuid=this.uuid,s.type=this.type,this.name!==""&&(s.name=this.name),this.castShadow===!0&&(s.castShadow=!0),this.receiveShadow===!0&&(s.receiveShadow=!0),this.visible===!1&&(s.visible=!1),this.frustumCulled===!1&&(s.frustumCulled=!1),this.renderOrder!==0&&(s.renderOrder=this.renderOrder),Object.keys(this.userData).length>0&&(s.userData=this.userData),s.layers=this.layers.mask,s.matrix=this.matrix.toArray(),s.up=this.up.toArray(),this.matrixAutoUpdate===!1&&(s.matrixAutoUpdate=!1),this.isInstancedMesh&&(s.type="InstancedMesh",s.count=this.count,s.instanceMatrix=this.instanceMatrix.toJSON(),this.instanceColor!==null&&(s.instanceColor=this.instanceColor.toJSON())),this.isBatchedMesh&&(s.type="BatchedMesh",s.perObjectFrustumCulled=this.perObjectFrustumCulled,s.sortObjects=this.sortObjects,s.drawRanges=this._drawRanges,s.reservedRanges=this._reservedRanges,s.geometryInfo=this._geometryInfo.map(o=>({...o,boundingBox:o.boundingBox?o.boundingBox.toJSON():void 0,boundingSphere:o.boundingSphere?o.boundingSphere.toJSON():void 0})),s.instanceInfo=this._instanceInfo.map(o=>({...o})),s.availableInstanceIds=this._availableInstanceIds.slice(),s.availableGeometryIds=this._availableGeometryIds.slice(),s.nextIndexStart=this._nextIndexStart,s.nextVertexStart=this._nextVertexStart,s.geometryCount=this._geometryCount,s.maxInstanceCount=this._maxInstanceCount,s.maxVertexCount=this._maxVertexCount,s.maxIndexCount=this._maxIndexCount,s.geometryInitialized=this._geometryInitialized,s.matricesTexture=this._matricesTexture.toJSON(e),s.indirectTexture=this._indirectTexture.toJSON(e),this._colorsTexture!==null&&(s.colorsTexture=this._colorsTexture.toJSON(e)),this.boundingSphere!==null&&(s.boundingSphere=this.boundingSphere.toJSON()),this.boundingBox!==null&&(s.boundingBox=this.boundingBox.toJSON()));function r(o,c){return o[c.uuid]===void 0&&(o[c.uuid]=c.toJSON(e)),c.uuid}if(this.isScene)this.background&&(this.background.isColor?s.background=this.background.toJSON():this.background.isTexture&&(s.background=this.background.toJSON(e).uuid)),this.environment&&this.environment.isTexture&&this.environment.isRenderTargetTexture!==!0&&(s.environment=this.environment.toJSON(e).uuid);else if(this.isMesh||this.isLine||this.isPoints){s.geometry=r(e.geometries,this.geometry);let o=this.geometry.parameters;if(o!==void 0&&o.shapes!==void 0){let c=o.shapes;if(Array.isArray(c))for(let l=0,u=c.length;l<u;l++){let h=c[l];r(e.shapes,h)}else r(e.shapes,c)}}if(this.isSkinnedMesh&&(s.bindMode=this.bindMode,s.bindMatrix=this.bindMatrix.toArray(),this.skeleton!==void 0&&(r(e.skeletons,this.skeleton),s.skeleton=this.skeleton.uuid)),this.material!==void 0)if(Array.isArray(this.material)){let o=[];for(let c=0,l=this.material.length;c<l;c++)o.push(r(e.materials,this.material[c]));s.material=o}else s.material=r(e.materials,this.material);if(this.children.length>0){s.children=[];for(let o=0;o<this.children.length;o++)s.children.push(this.children[o].toJSON(e).object)}if(this.animations.length>0){s.animations=[];for(let o=0;o<this.animations.length;o++){let c=this.animations[o];s.animations.push(r(e.animations,c))}}if(t){let o=a(e.geometries),c=a(e.materials),l=a(e.textures),u=a(e.images),h=a(e.shapes),d=a(e.skeletons),f=a(e.animations),g=a(e.nodes);o.length>0&&(i.geometries=o),c.length>0&&(i.materials=c),l.length>0&&(i.textures=l),u.length>0&&(i.images=u),h.length>0&&(i.shapes=h),d.length>0&&(i.skeletons=d),f.length>0&&(i.animations=f),g.length>0&&(i.nodes=g)}return i.object=s,i;function a(o){let c=[];for(let l in o){let u=o[l];delete u.metadata,c.push(u)}return c}}clone(e){return new this.constructor().copy(this,e)}copy(e,t=!0){if(this.name=e.name,this.up.copy(e.up),this.position.copy(e.position),this.rotation.order=e.rotation.order,this.quaternion.copy(e.quaternion),this.scale.copy(e.scale),this.matrix.copy(e.matrix),this.matrixWorld.copy(e.matrixWorld),this.matrixAutoUpdate=e.matrixAutoUpdate,this.matrixWorldAutoUpdate=e.matrixWorldAutoUpdate,this.matrixWorldNeedsUpdate=e.matrixWorldNeedsUpdate,this.layers.mask=e.layers.mask,this.visible=e.visible,this.castShadow=e.castShadow,this.receiveShadow=e.receiveShadow,this.frustumCulled=e.frustumCulled,this.renderOrder=e.renderOrder,this.animations=e.animations.slice(),this.userData=JSON.parse(JSON.stringify(e.userData)),t===!0)for(let i=0;i<e.children.length;i++){let s=e.children[i];this.add(s.clone())}return this}};Ft.DEFAULT_UP=new N(0,1,0);Ft.DEFAULT_MATRIX_AUTO_UPDATE=!0;Ft.DEFAULT_MATRIX_WORLD_AUTO_UPDATE=!0;var pn=new N,zn=new N,cl=new N,Vn=new N,ts=new N,ns=new N,Uh=new N,hl=new N,ul=new N,dl=new N,fl=new wt,pl=new wt,ml=new wt,ii=class n{constructor(e=new N,t=new N,i=new N){this.a=e,this.b=t,this.c=i}static getNormal(e,t,i,s){s.subVectors(i,t),pn.subVectors(e,t),s.cross(pn);let r=s.lengthSq();return r>0?s.multiplyScalar(1/Math.sqrt(r)):s.set(0,0,0)}static getBarycoord(e,t,i,s,r){pn.subVectors(s,t),zn.subVectors(i,t),cl.subVectors(e,t);let a=pn.dot(pn),o=pn.dot(zn),c=pn.dot(cl),l=zn.dot(zn),u=zn.dot(cl),h=a*l-o*o;if(h===0)return r.set(0,0,0),null;let d=1/h,f=(l*c-o*u)*d,g=(a*u-o*c)*d;return r.set(1-f-g,g,f)}static containsPoint(e,t,i,s){return this.getBarycoord(e,t,i,s,Vn)===null?!1:Vn.x>=0&&Vn.y>=0&&Vn.x+Vn.y<=1}static getInterpolation(e,t,i,s,r,a,o,c){return this.getBarycoord(e,t,i,s,Vn)===null?(c.x=0,c.y=0,"z"in c&&(c.z=0),"w"in c&&(c.w=0),null):(c.setScalar(0),c.addScaledVector(r,Vn.x),c.addScaledVector(a,Vn.y),c.addScaledVector(o,Vn.z),c)}static getInterpolatedAttribute(e,t,i,s,r,a){return fl.setScalar(0),pl.setScalar(0),ml.setScalar(0),fl.fromBufferAttribute(e,t),pl.fromBufferAttribute(e,i),ml.fromBufferAttribute(e,s),a.setScalar(0),a.addScaledVector(fl,r.x),a.addScaledVector(pl,r.y),a.addScaledVector(ml,r.z),a}static isFrontFacing(e,t,i,s){return pn.subVectors(i,t),zn.subVectors(e,t),pn.cross(zn).dot(s)<0}set(e,t,i){return this.a.copy(e),this.b.copy(t),this.c.copy(i),this}setFromPointsAndIndices(e,t,i,s){return this.a.copy(e[t]),this.b.copy(e[i]),this.c.copy(e[s]),this}setFromAttributeAndIndices(e,t,i,s){return this.a.fromBufferAttribute(e,t),this.b.fromBufferAttribute(e,i),this.c.fromBufferAttribute(e,s),this}clone(){return new this.constructor().copy(this)}copy(e){return this.a.copy(e.a),this.b.copy(e.b),this.c.copy(e.c),this}getArea(){return pn.subVectors(this.c,this.b),zn.subVectors(this.a,this.b),pn.cross(zn).length()*.5}getMidpoint(e){return e.addVectors(this.a,this.b).add(this.c).multiplyScalar(1/3)}getNormal(e){return n.getNormal(this.a,this.b,this.c,e)}getPlane(e){return e.setFromCoplanarPoints(this.a,this.b,this.c)}getBarycoord(e,t){return n.getBarycoord(e,this.a,this.b,this.c,t)}getInterpolation(e,t,i,s,r){return n.getInterpolation(e,this.a,this.b,this.c,t,i,s,r)}containsPoint(e){return n.containsPoint(e,this.a,this.b,this.c)}isFrontFacing(e){return n.isFrontFacing(this.a,this.b,this.c,e)}intersectsBox(e){return e.intersectsTriangle(this)}closestPointToPoint(e,t){let i=this.a,s=this.b,r=this.c,a,o;ts.subVectors(s,i),ns.subVectors(r,i),hl.subVectors(e,i);let c=ts.dot(hl),l=ns.dot(hl);if(c<=0&&l<=0)return t.copy(i);ul.subVectors(e,s);let u=ts.dot(ul),h=ns.dot(ul);if(u>=0&&h<=u)return t.copy(s);let d=c*h-u*l;if(d<=0&&c>=0&&u<=0)return a=c/(c-u),t.copy(i).addScaledVector(ts,a);dl.subVectors(e,r);let f=ts.dot(dl),g=ns.dot(dl);if(g>=0&&f<=g)return t.copy(r);let x=f*l-c*g;if(x<=0&&l>=0&&g<=0)return o=l/(l-g),t.copy(i).addScaledVector(ns,o);let m=u*g-f*h;if(m<=0&&h-u>=0&&f-g>=0)return Uh.subVectors(r,s),o=(h-u)/(h-u+(f-g)),t.copy(s).addScaledVector(Uh,o);let p=1/(m+x+d);return a=x*p,o=d*p,t.copy(i).addScaledVector(ts,a).addScaledVector(ns,o)}equals(e){return e.a.equals(this.a)&&e.b.equals(this.b)&&e.c.equals(this.c)}},Uu={aliceblue:15792383,antiquewhite:16444375,aqua:65535,aquamarine:8388564,azure:15794175,beige:16119260,bisque:16770244,black:0,blanchedalmond:16772045,blue:255,blueviolet:9055202,brown:10824234,burlywood:14596231,cadetblue:6266528,chartreuse:8388352,chocolate:13789470,coral:16744272,cornflowerblue:6591981,cornsilk:16775388,crimson:14423100,cyan:65535,darkblue:139,darkcyan:35723,darkgoldenrod:12092939,darkgray:11119017,darkgreen:25600,darkgrey:11119017,darkkhaki:12433259,darkmagenta:9109643,darkolivegreen:5597999,darkorange:16747520,darkorchid:10040012,darkred:9109504,darksalmon:15308410,darkseagreen:9419919,darkslateblue:4734347,darkslategray:3100495,darkslategrey:3100495,darkturquoise:52945,darkviolet:9699539,deeppink:16716947,deepskyblue:49151,dimgray:6908265,dimgrey:6908265,dodgerblue:2003199,firebrick:11674146,floralwhite:16775920,forestgreen:2263842,fuchsia:16711935,gainsboro:14474460,ghostwhite:16316671,gold:16766720,goldenrod:14329120,gray:8421504,green:32768,greenyellow:11403055,grey:8421504,honeydew:15794160,hotpink:16738740,indianred:13458524,indigo:4915330,ivory:16777200,khaki:15787660,lavender:15132410,lavenderblush:16773365,lawngreen:8190976,lemonchiffon:16775885,lightblue:11393254,lightcoral:15761536,lightcyan:14745599,lightgoldenrodyellow:16448210,lightgray:13882323,lightgreen:9498256,lightgrey:13882323,lightpink:16758465,lightsalmon:16752762,lightseagreen:2142890,lightskyblue:8900346,lightslategray:7833753,lightslategrey:7833753,lightsteelblue:11584734,lightyellow:16777184,lime:65280,limegreen:3329330,linen:16445670,magenta:16711935,maroon:8388608,mediumaquamarine:6737322,mediumblue:205,mediumorchid:12211667,mediumpurple:9662683,mediumseagreen:3978097,mediumslateblue:8087790,mediumspringgreen:64154,mediumturquoise:4772300,mediumvioletred:13047173,midnightblue:1644912,mintcream:16121850,mistyrose:16770273,moccasin:16770229,navajowhite:16768685,navy:128,oldlace:16643558,olive:8421376,olivedrab:7048739,orange:16753920,orangered:16729344,orchid:14315734,palegoldenrod:15657130,palegreen:10025880,paleturquoise:11529966,palevioletred:14381203,papayawhip:16773077,peachpuff:16767673,peru:13468991,pink:16761035,plum:14524637,powderblue:11591910,purple:8388736,rebeccapurple:6697881,red:16711680,rosybrown:12357519,royalblue:4286945,saddlebrown:9127187,salmon:16416882,sandybrown:16032864,seagreen:3050327,seashell:16774638,sienna:10506797,silver:12632256,skyblue:8900331,slateblue:6970061,slategray:7372944,slategrey:7372944,snow:16775930,springgreen:65407,steelblue:4620980,tan:13808780,teal:32896,thistle:14204888,tomato:16737095,turquoise:4251856,violet:15631086,wheat:16113331,white:16777215,whitesmoke:16119285,yellow:16776960,yellowgreen:10145074},ti={h:0,s:0,l:0},Jr={h:0,s:0,l:0};function gl(n,e,t){return t<0&&(t+=1),t>1&&(t-=1),t<1/6?n+(e-n)*6*t:t<1/2?e:t<2/3?n+(e-n)*6*(2/3-t):n}var qe=class{constructor(e,t,i){return this.isColor=!0,this.r=1,this.g=1,this.b=1,this.set(e,t,i)}set(e,t,i){if(t===void 0&&i===void 0){let s=e;s&&s.isColor?this.copy(s):typeof s=="number"?this.setHex(s):typeof s=="string"&&this.setStyle(s)}else this.setRGB(e,t,i);return this}setScalar(e){return this.r=e,this.g=e,this.b=e,this}setHex(e,t=It){return e=Math.floor(e),this.r=(e>>16&255)/255,this.g=(e>>8&255)/255,this.b=(e&255)/255,st.colorSpaceToWorking(this,t),this}setRGB(e,t,i,s=st.workingColorSpace){return this.r=e,this.g=t,this.b=i,st.colorSpaceToWorking(this,s),this}setHSL(e,t,i,s=st.workingColorSpace){if(e=nc(e,1),t=Je(t,0,1),i=Je(i,0,1),t===0)this.r=this.g=this.b=i;else{let r=i<=.5?i*(1+t):i+t-i*t,a=2*i-r;this.r=gl(a,r,e+1/3),this.g=gl(a,r,e),this.b=gl(a,r,e-1/3)}return st.colorSpaceToWorking(this,s),this}setStyle(e,t=It){function i(r){r!==void 0&&parseFloat(r)<1&&console.warn("THREE.Color: Alpha component of "+e+" will be ignored.")}let s;if(s=/^(\w+)\(([^\)]*)\)/.exec(e)){let r,a=s[1],o=s[2];switch(a){case"rgb":case"rgba":if(r=/^\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return i(r[4]),this.setRGB(Math.min(255,parseInt(r[1],10))/255,Math.min(255,parseInt(r[2],10))/255,Math.min(255,parseInt(r[3],10))/255,t);if(r=/^\s*(\d+)\%\s*,\s*(\d+)\%\s*,\s*(\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return i(r[4]),this.setRGB(Math.min(100,parseInt(r[1],10))/100,Math.min(100,parseInt(r[2],10))/100,Math.min(100,parseInt(r[3],10))/100,t);break;case"hsl":case"hsla":if(r=/^\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\%\s*,\s*(\d*\.?\d+)\%\s*(?:,\s*(\d*\.?\d+)\s*)?$/.exec(o))return i(r[4]),this.setHSL(parseFloat(r[1])/360,parseFloat(r[2])/100,parseFloat(r[3])/100,t);break;default:console.warn("THREE.Color: Unknown color model "+e)}}else if(s=/^\#([A-Fa-f\d]+)$/.exec(e)){let r=s[1],a=r.length;if(a===3)return this.setRGB(parseInt(r.charAt(0),16)/15,parseInt(r.charAt(1),16)/15,parseInt(r.charAt(2),16)/15,t);if(a===6)return this.setHex(parseInt(r,16),t);console.warn("THREE.Color: Invalid hex color "+e)}else if(e&&e.length>0)return this.setColorName(e,t);return this}setColorName(e,t=It){let i=Uu[e.toLowerCase()];return i!==void 0?this.setHex(i,t):console.warn("THREE.Color: Unknown color "+e),this}clone(){return new this.constructor(this.r,this.g,this.b)}copy(e){return this.r=e.r,this.g=e.g,this.b=e.b,this}copySRGBToLinear(e){return this.r=Gn(e.r),this.g=Gn(e.g),this.b=Gn(e.b),this}copyLinearToSRGB(e){return this.r=os(e.r),this.g=os(e.g),this.b=os(e.b),this}convertSRGBToLinear(){return this.copySRGBToLinear(this),this}convertLinearToSRGB(){return this.copyLinearToSRGB(this),this}getHex(e=It){return st.workingToColorSpace(Lt.copy(this),e),Math.round(Je(Lt.r*255,0,255))*65536+Math.round(Je(Lt.g*255,0,255))*256+Math.round(Je(Lt.b*255,0,255))}getHexString(e=It){return("000000"+this.getHex(e).toString(16)).slice(-6)}getHSL(e,t=st.workingColorSpace){st.workingToColorSpace(Lt.copy(this),t);let i=Lt.r,s=Lt.g,r=Lt.b,a=Math.max(i,s,r),o=Math.min(i,s,r),c,l,u=(o+a)/2;if(o===a)c=0,l=0;else{let h=a-o;switch(l=u<=.5?h/(a+o):h/(2-a-o),a){case i:c=(s-r)/h+(s<r?6:0);break;case s:c=(r-i)/h+2;break;case r:c=(i-s)/h+4;break}c/=6}return e.h=c,e.s=l,e.l=u,e}getRGB(e,t=st.workingColorSpace){return st.workingToColorSpace(Lt.copy(this),t),e.r=Lt.r,e.g=Lt.g,e.b=Lt.b,e}getStyle(e=It){st.workingToColorSpace(Lt.copy(this),e);let t=Lt.r,i=Lt.g,s=Lt.b;return e!==It?`color(${e} ${t.toFixed(3)} ${i.toFixed(3)} ${s.toFixed(3)})`:`rgb(${Math.round(t*255)},${Math.round(i*255)},${Math.round(s*255)})`}offsetHSL(e,t,i){return this.getHSL(ti),this.setHSL(ti.h+e,ti.s+t,ti.l+i)}add(e){return this.r+=e.r,this.g+=e.g,this.b+=e.b,this}addColors(e,t){return this.r=e.r+t.r,this.g=e.g+t.g,this.b=e.b+t.b,this}addScalar(e){return this.r+=e,this.g+=e,this.b+=e,this}sub(e){return this.r=Math.max(0,this.r-e.r),this.g=Math.max(0,this.g-e.g),this.b=Math.max(0,this.b-e.b),this}multiply(e){return this.r*=e.r,this.g*=e.g,this.b*=e.b,this}multiplyScalar(e){return this.r*=e,this.g*=e,this.b*=e,this}lerp(e,t){return this.r+=(e.r-this.r)*t,this.g+=(e.g-this.g)*t,this.b+=(e.b-this.b)*t,this}lerpColors(e,t,i){return this.r=e.r+(t.r-e.r)*i,this.g=e.g+(t.g-e.g)*i,this.b=e.b+(t.b-e.b)*i,this}lerpHSL(e,t){this.getHSL(ti),e.getHSL(Jr);let i=Gs(ti.h,Jr.h,t),s=Gs(ti.s,Jr.s,t),r=Gs(ti.l,Jr.l,t);return this.setHSL(i,s,r),this}setFromVector3(e){return this.r=e.x,this.g=e.y,this.b=e.z,this}applyMatrix3(e){let t=this.r,i=this.g,s=this.b,r=e.elements;return this.r=r[0]*t+r[3]*i+r[6]*s,this.g=r[1]*t+r[4]*i+r[7]*s,this.b=r[2]*t+r[5]*i+r[8]*s,this}equals(e){return e.r===this.r&&e.g===this.g&&e.b===this.b}fromArray(e,t=0){return this.r=e[t],this.g=e[t+1],this.b=e[t+2],this}toArray(e=[],t=0){return e[t]=this.r,e[t+1]=this.g,e[t+2]=this.b,e}fromBufferAttribute(e,t){return this.r=e.getX(t),this.g=e.getY(t),this.b=e.getZ(t),this}toJSON(){return this.getHex()}*[Symbol.iterator](){yield this.r,yield this.g,yield this.b}},Lt=new qe;qe.NAMES=Uu;var jf=0,ai=class extends Mn{constructor(){super(),this.isMaterial=!0,Object.defineProperty(this,"id",{value:jf++}),this.uuid=Fi(),this.name="",this.type="Material",this.blending=Ai,this.side=Wn,this.vertexColors=!1,this.opacity=1,this.transparent=!1,this.alphaHash=!1,this.blendSrc=ua,this.blendDst=da,this.blendEquation=ri,this.blendSrcAlpha=null,this.blendDstAlpha=null,this.blendEquationAlpha=null,this.blendColor=new qe(0,0,0),this.blendAlpha=0,this.depthFunc=Ci,this.depthTest=!0,this.depthWrite=!0,this.stencilWriteMask=255,this.stencilFunc=Al,this.stencilRef=0,this.stencilFuncMask=255,this.stencilFail=Si,this.stencilZFail=Si,this.stencilZPass=Si,this.stencilWrite=!1,this.clippingPlanes=null,this.clipIntersection=!1,this.clipShadows=!1,this.shadowSide=null,this.colorWrite=!0,this.precision=null,this.polygonOffset=!1,this.polygonOffsetFactor=0,this.polygonOffsetUnits=0,this.dithering=!1,this.alphaToCoverage=!1,this.premultipliedAlpha=!1,this.forceSinglePass=!1,this.allowOverride=!0,this.visible=!0,this.toneMapped=!0,this.userData={},this.version=0,this._alphaTest=0}get alphaTest(){return this._alphaTest}set alphaTest(e){this._alphaTest>0!=e>0&&this.version++,this._alphaTest=e}onBeforeRender(){}onBeforeCompile(){}customProgramCacheKey(){return this.onBeforeCompile.toString()}setValues(e){if(e!==void 0)for(let t in e){let i=e[t];if(i===void 0){console.warn(`THREE.Material: parameter '${t}' has value of undefined.`);continue}let s=this[t];if(s===void 0){console.warn(`THREE.Material: '${t}' is not a property of THREE.${this.type}.`);continue}s&&s.isColor?s.set(i):s&&s.isVector3&&i&&i.isVector3?s.copy(i):this[t]=i}}toJSON(e){let t=e===void 0||typeof e=="string";t&&(e={textures:{},images:{}});let i={metadata:{version:4.7,type:"Material",generator:"Material.toJSON"}};i.uuid=this.uuid,i.type=this.type,this.name!==""&&(i.name=this.name),this.color&&this.color.isColor&&(i.color=this.color.getHex()),this.roughness!==void 0&&(i.roughness=this.roughness),this.metalness!==void 0&&(i.metalness=this.metalness),this.sheen!==void 0&&(i.sheen=this.sheen),this.sheenColor&&this.sheenColor.isColor&&(i.sheenColor=this.sheenColor.getHex()),this.sheenRoughness!==void 0&&(i.sheenRoughness=this.sheenRoughness),this.emissive&&this.emissive.isColor&&(i.emissive=this.emissive.getHex()),this.emissiveIntensity!==void 0&&this.emissiveIntensity!==1&&(i.emissiveIntensity=this.emissiveIntensity),this.specular&&this.specular.isColor&&(i.specular=this.specular.getHex()),this.specularIntensity!==void 0&&(i.specularIntensity=this.specularIntensity),this.specularColor&&this.specularColor.isColor&&(i.specularColor=this.specularColor.getHex()),this.shininess!==void 0&&(i.shininess=this.shininess),this.clearcoat!==void 0&&(i.clearcoat=this.clearcoat),this.clearcoatRoughness!==void 0&&(i.clearcoatRoughness=this.clearcoatRoughness),this.clearcoatMap&&this.clearcoatMap.isTexture&&(i.clearcoatMap=this.clearcoatMap.toJSON(e).uuid),this.clearcoatRoughnessMap&&this.clearcoatRoughnessMap.isTexture&&(i.clearcoatRoughnessMap=this.clearcoatRoughnessMap.toJSON(e).uuid),this.clearcoatNormalMap&&this.clearcoatNormalMap.isTexture&&(i.clearcoatNormalMap=this.clearcoatNormalMap.toJSON(e).uuid,i.clearcoatNormalScale=this.clearcoatNormalScale.toArray()),this.sheenColorMap&&this.sheenColorMap.isTexture&&(i.sheenColorMap=this.sheenColorMap.toJSON(e).uuid),this.sheenRoughnessMap&&this.sheenRoughnessMap.isTexture&&(i.sheenRoughnessMap=this.sheenRoughnessMap.toJSON(e).uuid),this.dispersion!==void 0&&(i.dispersion=this.dispersion),this.iridescence!==void 0&&(i.iridescence=this.iridescence),this.iridescenceIOR!==void 0&&(i.iridescenceIOR=this.iridescenceIOR),this.iridescenceThicknessRange!==void 0&&(i.iridescenceThicknessRange=this.iridescenceThicknessRange),this.iridescenceMap&&this.iridescenceMap.isTexture&&(i.iridescenceMap=this.iridescenceMap.toJSON(e).uuid),this.iridescenceThicknessMap&&this.iridescenceThicknessMap.isTexture&&(i.iridescenceThicknessMap=this.iridescenceThicknessMap.toJSON(e).uuid),this.anisotropy!==void 0&&(i.anisotropy=this.anisotropy),this.anisotropyRotation!==void 0&&(i.anisotropyRotation=this.anisotropyRotation),this.anisotropyMap&&this.anisotropyMap.isTexture&&(i.anisotropyMap=this.anisotropyMap.toJSON(e).uuid),this.map&&this.map.isTexture&&(i.map=this.map.toJSON(e).uuid),this.matcap&&this.matcap.isTexture&&(i.matcap=this.matcap.toJSON(e).uuid),this.alphaMap&&this.alphaMap.isTexture&&(i.alphaMap=this.alphaMap.toJSON(e).uuid),this.lightMap&&this.lightMap.isTexture&&(i.lightMap=this.lightMap.toJSON(e).uuid,i.lightMapIntensity=this.lightMapIntensity),this.aoMap&&this.aoMap.isTexture&&(i.aoMap=this.aoMap.toJSON(e).uuid,i.aoMapIntensity=this.aoMapIntensity),this.bumpMap&&this.bumpMap.isTexture&&(i.bumpMap=this.bumpMap.toJSON(e).uuid,i.bumpScale=this.bumpScale),this.normalMap&&this.normalMap.isTexture&&(i.normalMap=this.normalMap.toJSON(e).uuid,i.normalMapType=this.normalMapType,i.normalScale=this.normalScale.toArray()),this.displacementMap&&this.displacementMap.isTexture&&(i.displacementMap=this.displacementMap.toJSON(e).uuid,i.displacementScale=this.displacementScale,i.displacementBias=this.displacementBias),this.roughnessMap&&this.roughnessMap.isTexture&&(i.roughnessMap=this.roughnessMap.toJSON(e).uuid),this.metalnessMap&&this.metalnessMap.isTexture&&(i.metalnessMap=this.metalnessMap.toJSON(e).uuid),this.emissiveMap&&this.emissiveMap.isTexture&&(i.emissiveMap=this.emissiveMap.toJSON(e).uuid),this.specularMap&&this.specularMap.isTexture&&(i.specularMap=this.specularMap.toJSON(e).uuid),this.specularIntensityMap&&this.specularIntensityMap.isTexture&&(i.specularIntensityMap=this.specularIntensityMap.toJSON(e).uuid),this.specularColorMap&&this.specularColorMap.isTexture&&(i.specularColorMap=this.specularColorMap.toJSON(e).uuid),this.envMap&&this.envMap.isTexture&&(i.envMap=this.envMap.toJSON(e).uuid,this.combine!==void 0&&(i.combine=this.combine)),this.envMapRotation!==void 0&&(i.envMapRotation=this.envMapRotation.toArray()),this.envMapIntensity!==void 0&&(i.envMapIntensity=this.envMapIntensity),this.reflectivity!==void 0&&(i.reflectivity=this.reflectivity),this.refractionRatio!==void 0&&(i.refractionRatio=this.refractionRatio),this.gradientMap&&this.gradientMap.isTexture&&(i.gradientMap=this.gradientMap.toJSON(e).uuid),this.transmission!==void 0&&(i.transmission=this.transmission),this.transmissionMap&&this.transmissionMap.isTexture&&(i.transmissionMap=this.transmissionMap.toJSON(e).uuid),this.thickness!==void 0&&(i.thickness=this.thickness),this.thicknessMap&&this.thicknessMap.isTexture&&(i.thicknessMap=this.thicknessMap.toJSON(e).uuid),this.attenuationDistance!==void 0&&this.attenuationDistance!==1/0&&(i.attenuationDistance=this.attenuationDistance),this.attenuationColor!==void 0&&(i.attenuationColor=this.attenuationColor.getHex()),this.size!==void 0&&(i.size=this.size),this.shadowSide!==null&&(i.shadowSide=this.shadowSide),this.sizeAttenuation!==void 0&&(i.sizeAttenuation=this.sizeAttenuation),this.blending!==Ai&&(i.blending=this.blending),this.side!==Wn&&(i.side=this.side),this.vertexColors===!0&&(i.vertexColors=!0),this.opacity<1&&(i.opacity=this.opacity),this.transparent===!0&&(i.transparent=!0),this.blendSrc!==ua&&(i.blendSrc=this.blendSrc),this.blendDst!==da&&(i.blendDst=this.blendDst),this.blendEquation!==ri&&(i.blendEquation=this.blendEquation),this.blendSrcAlpha!==null&&(i.blendSrcAlpha=this.blendSrcAlpha),this.blendDstAlpha!==null&&(i.blendDstAlpha=this.blendDstAlpha),this.blendEquationAlpha!==null&&(i.blendEquationAlpha=this.blendEquationAlpha),this.blendColor&&this.blendColor.isColor&&(i.blendColor=this.blendColor.getHex()),this.blendAlpha!==0&&(i.blendAlpha=this.blendAlpha),this.depthFunc!==Ci&&(i.depthFunc=this.depthFunc),this.depthTest===!1&&(i.depthTest=this.depthTest),this.depthWrite===!1&&(i.depthWrite=this.depthWrite),this.colorWrite===!1&&(i.colorWrite=this.colorWrite),this.stencilWriteMask!==255&&(i.stencilWriteMask=this.stencilWriteMask),this.stencilFunc!==Al&&(i.stencilFunc=this.stencilFunc),this.stencilRef!==0&&(i.stencilRef=this.stencilRef),this.stencilFuncMask!==255&&(i.stencilFuncMask=this.stencilFuncMask),this.stencilFail!==Si&&(i.stencilFail=this.stencilFail),this.stencilZFail!==Si&&(i.stencilZFail=this.stencilZFail),this.stencilZPass!==Si&&(i.stencilZPass=this.stencilZPass),this.stencilWrite===!0&&(i.stencilWrite=this.stencilWrite),this.rotation!==void 0&&this.rotation!==0&&(i.rotation=this.rotation),this.polygonOffset===!0&&(i.polygonOffset=!0),this.polygonOffsetFactor!==0&&(i.polygonOffsetFactor=this.polygonOffsetFactor),this.polygonOffsetUnits!==0&&(i.polygonOffsetUnits=this.polygonOffsetUnits),this.linewidth!==void 0&&this.linewidth!==1&&(i.linewidth=this.linewidth),this.dashSize!==void 0&&(i.dashSize=this.dashSize),this.gapSize!==void 0&&(i.gapSize=this.gapSize),this.scale!==void 0&&(i.scale=this.scale),this.dithering===!0&&(i.dithering=!0),this.alphaTest>0&&(i.alphaTest=this.alphaTest),this.alphaHash===!0&&(i.alphaHash=!0),this.alphaToCoverage===!0&&(i.alphaToCoverage=!0),this.premultipliedAlpha===!0&&(i.premultipliedAlpha=!0),this.forceSinglePass===!0&&(i.forceSinglePass=!0),this.wireframe===!0&&(i.wireframe=!0),this.wireframeLinewidth>1&&(i.wireframeLinewidth=this.wireframeLinewidth),this.wireframeLinecap!=="round"&&(i.wireframeLinecap=this.wireframeLinecap),this.wireframeLinejoin!=="round"&&(i.wireframeLinejoin=this.wireframeLinejoin),this.flatShading===!0&&(i.flatShading=!0),this.visible===!1&&(i.visible=!1),this.toneMapped===!1&&(i.toneMapped=!1),this.fog===!1&&(i.fog=!1),Object.keys(this.userData).length>0&&(i.userData=this.userData);function s(r){let a=[];for(let o in r){let c=r[o];delete c.metadata,a.push(c)}return a}if(t){let r=s(e.textures),a=s(e.images);r.length>0&&(i.textures=r),a.length>0&&(i.images=a)}return i}clone(){return new this.constructor().copy(this)}copy(e){this.name=e.name,this.blending=e.blending,this.side=e.side,this.vertexColors=e.vertexColors,this.opacity=e.opacity,this.transparent=e.transparent,this.blendSrc=e.blendSrc,this.blendDst=e.blendDst,this.blendEquation=e.blendEquation,this.blendSrcAlpha=e.blendSrcAlpha,this.blendDstAlpha=e.blendDstAlpha,this.blendEquationAlpha=e.blendEquationAlpha,this.blendColor.copy(e.blendColor),this.blendAlpha=e.blendAlpha,this.depthFunc=e.depthFunc,this.depthTest=e.depthTest,this.depthWrite=e.depthWrite,this.stencilWriteMask=e.stencilWriteMask,this.stencilFunc=e.stencilFunc,this.stencilRef=e.stencilRef,this.stencilFuncMask=e.stencilFuncMask,this.stencilFail=e.stencilFail,this.stencilZFail=e.stencilZFail,this.stencilZPass=e.stencilZPass,this.stencilWrite=e.stencilWrite;let t=e.clippingPlanes,i=null;if(t!==null){let s=t.length;i=new Array(s);for(let r=0;r!==s;++r)i[r]=t[r].clone()}return this.clippingPlanes=i,this.clipIntersection=e.clipIntersection,this.clipShadows=e.clipShadows,this.shadowSide=e.shadowSide,this.colorWrite=e.colorWrite,this.precision=e.precision,this.polygonOffset=e.polygonOffset,this.polygonOffsetFactor=e.polygonOffsetFactor,this.polygonOffsetUnits=e.polygonOffsetUnits,this.dithering=e.dithering,this.alphaTest=e.alphaTest,this.alphaHash=e.alphaHash,this.alphaToCoverage=e.alphaToCoverage,this.premultipliedAlpha=e.premultipliedAlpha,this.forceSinglePass=e.forceSinglePass,this.visible=e.visible,this.toneMapped=e.toneMapped,this.userData=JSON.parse(JSON.stringify(e.userData)),this}dispose(){this.dispatchEvent({type:"dispose"})}set needsUpdate(e){e===!0&&this.version++}},js=class extends ai{constructor(e){super(),this.isMeshBasicMaterial=!0,this.type="MeshBasicMaterial",this.color=new qe(16777215),this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.specularMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new _n,this.combine=Gl,this.reflectivity=1,this.refractionRatio=.98,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.color.copy(e.color),this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.specularMap=e.specularMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.combine=e.combine,this.reflectivity=e.reflectivity,this.refractionRatio=e.refractionRatio,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.fog=e.fog,this}};var St=new N,Kr=new de,Qf=0,Nt=class{constructor(e,t,i=!1){if(Array.isArray(e))throw new TypeError("THREE.BufferAttribute: array should be a Typed Array.");this.isBufferAttribute=!0,Object.defineProperty(this,"id",{value:Qf++}),this.name="",this.array=e,this.itemSize=t,this.count=e!==void 0?e.length/t:0,this.normalized=i,this.usage=Cl,this.updateRanges=[],this.gpuType=Cn,this.version=0}onUploadCallback(){}set needsUpdate(e){e===!0&&this.version++}setUsage(e){return this.usage=e,this}addUpdateRange(e,t){this.updateRanges.push({start:e,count:t})}clearUpdateRanges(){this.updateRanges.length=0}copy(e){return this.name=e.name,this.array=new e.array.constructor(e.array),this.itemSize=e.itemSize,this.count=e.count,this.normalized=e.normalized,this.usage=e.usage,this.gpuType=e.gpuType,this}copyAt(e,t,i){e*=this.itemSize,i*=t.itemSize;for(let s=0,r=this.itemSize;s<r;s++)this.array[e+s]=t.array[i+s];return this}copyArray(e){return this.array.set(e),this}applyMatrix3(e){if(this.itemSize===2)for(let t=0,i=this.count;t<i;t++)Kr.fromBufferAttribute(this,t),Kr.applyMatrix3(e),this.setXY(t,Kr.x,Kr.y);else if(this.itemSize===3)for(let t=0,i=this.count;t<i;t++)St.fromBufferAttribute(this,t),St.applyMatrix3(e),this.setXYZ(t,St.x,St.y,St.z);return this}applyMatrix4(e){for(let t=0,i=this.count;t<i;t++)St.fromBufferAttribute(this,t),St.applyMatrix4(e),this.setXYZ(t,St.x,St.y,St.z);return this}applyNormalMatrix(e){for(let t=0,i=this.count;t<i;t++)St.fromBufferAttribute(this,t),St.applyNormalMatrix(e),this.setXYZ(t,St.x,St.y,St.z);return this}transformDirection(e){for(let t=0,i=this.count;t<i;t++)St.fromBufferAttribute(this,t),St.transformDirection(e),this.setXYZ(t,St.x,St.y,St.z);return this}set(e,t=0){return this.array.set(e,t),this}getComponent(e,t){let i=this.array[e*this.itemSize+t];return this.normalized&&(i=as(i,this.array)),i}setComponent(e,t,i){return this.normalized&&(i=Ht(i,this.array)),this.array[e*this.itemSize+t]=i,this}getX(e){let t=this.array[e*this.itemSize];return this.normalized&&(t=as(t,this.array)),t}setX(e,t){return this.normalized&&(t=Ht(t,this.array)),this.array[e*this.itemSize]=t,this}getY(e){let t=this.array[e*this.itemSize+1];return this.normalized&&(t=as(t,this.array)),t}setY(e,t){return this.normalized&&(t=Ht(t,this.array)),this.array[e*this.itemSize+1]=t,this}getZ(e){let t=this.array[e*this.itemSize+2];return this.normalized&&(t=as(t,this.array)),t}setZ(e,t){return this.normalized&&(t=Ht(t,this.array)),this.array[e*this.itemSize+2]=t,this}getW(e){let t=this.array[e*this.itemSize+3];return this.normalized&&(t=as(t,this.array)),t}setW(e,t){return this.normalized&&(t=Ht(t,this.array)),this.array[e*this.itemSize+3]=t,this}setXY(e,t,i){return e*=this.itemSize,this.normalized&&(t=Ht(t,this.array),i=Ht(i,this.array)),this.array[e+0]=t,this.array[e+1]=i,this}setXYZ(e,t,i,s){return e*=this.itemSize,this.normalized&&(t=Ht(t,this.array),i=Ht(i,this.array),s=Ht(s,this.array)),this.array[e+0]=t,this.array[e+1]=i,this.array[e+2]=s,this}setXYZW(e,t,i,s,r){return e*=this.itemSize,this.normalized&&(t=Ht(t,this.array),i=Ht(i,this.array),s=Ht(s,this.array),r=Ht(r,this.array)),this.array[e+0]=t,this.array[e+1]=i,this.array[e+2]=s,this.array[e+3]=r,this}onUpload(e){return this.onUploadCallback=e,this}clone(){return new this.constructor(this.array,this.itemSize).copy(this)}toJSON(){let e={itemSize:this.itemSize,type:this.array.constructor.name,array:Array.from(this.array),normalized:this.normalized};return this.name!==""&&(e.name=this.name),this.usage!==Cl&&(e.usage=this.usage),e}};var Qs=class extends Nt{constructor(e,t,i){super(new Uint16Array(e),t,i)}};var er=class extends Nt{constructor(e,t,i){super(new Uint32Array(e),t,i)}};var Gt=class extends Nt{constructor(e,t,i){super(new Float32Array(e),t,i)}},ep=0,rn=new Mt,_l=new Ft,is=new N,Qt=new Tn,zs=new Tn,Pt=new N,cn=class n extends Mn{constructor(){super(),this.isBufferGeometry=!0,Object.defineProperty(this,"id",{value:ep++}),this.uuid=Fi(),this.name="",this.type="BufferGeometry",this.index=null,this.indirect=null,this.attributes={},this.morphAttributes={},this.morphTargetsRelative=!1,this.groups=[],this.boundingBox=null,this.boundingSphere=null,this.drawRange={start:0,count:1/0},this.userData={}}getIndex(){return this.index}setIndex(e){return Array.isArray(e)?this.index=new(sc(e)?er:Qs)(e,1):this.index=e,this}setIndirect(e){return this.indirect=e,this}getIndirect(){return this.indirect}getAttribute(e){return this.attributes[e]}setAttribute(e,t){return this.attributes[e]=t,this}deleteAttribute(e){return delete this.attributes[e],this}hasAttribute(e){return this.attributes[e]!==void 0}addGroup(e,t,i=0){this.groups.push({start:e,count:t,materialIndex:i})}clearGroups(){this.groups=[]}setDrawRange(e,t){this.drawRange.start=e,this.drawRange.count=t}applyMatrix4(e){let t=this.attributes.position;t!==void 0&&(t.applyMatrix4(e),t.needsUpdate=!0);let i=this.attributes.normal;if(i!==void 0){let r=new $e().getNormalMatrix(e);i.applyNormalMatrix(r),i.needsUpdate=!0}let s=this.attributes.tangent;return s!==void 0&&(s.transformDirection(e),s.needsUpdate=!0),this.boundingBox!==null&&this.computeBoundingBox(),this.boundingSphere!==null&&this.computeBoundingSphere(),this}applyQuaternion(e){return rn.makeRotationFromQuaternion(e),this.applyMatrix4(rn),this}rotateX(e){return rn.makeRotationX(e),this.applyMatrix4(rn),this}rotateY(e){return rn.makeRotationY(e),this.applyMatrix4(rn),this}rotateZ(e){return rn.makeRotationZ(e),this.applyMatrix4(rn),this}translate(e,t,i){return rn.makeTranslation(e,t,i),this.applyMatrix4(rn),this}scale(e,t,i){return rn.makeScale(e,t,i),this.applyMatrix4(rn),this}lookAt(e){return _l.lookAt(e),_l.updateMatrix(),this.applyMatrix4(_l.matrix),this}center(){return this.computeBoundingBox(),this.boundingBox.getCenter(is).negate(),this.translate(is.x,is.y,is.z),this}setFromPoints(e){let t=this.getAttribute("position");if(t===void 0){let i=[];for(let s=0,r=e.length;s<r;s++){let a=e[s];i.push(a.x,a.y,a.z||0)}this.setAttribute("position",new Gt(i,3))}else{let i=Math.min(e.length,t.count);for(let s=0;s<i;s++){let r=e[s];t.setXYZ(s,r.x,r.y,r.z||0)}e.length>t.count&&console.warn("THREE.BufferGeometry: Buffer size too small for points data. Use .dispose() and create a new geometry."),t.needsUpdate=!0}return this}computeBoundingBox(){this.boundingBox===null&&(this.boundingBox=new Tn);let e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingBox(): GLBufferAttribute requires a manual bounding box.",this),this.boundingBox.set(new N(-1/0,-1/0,-1/0),new N(1/0,1/0,1/0));return}if(e!==void 0){if(this.boundingBox.setFromBufferAttribute(e),t)for(let i=0,s=t.length;i<s;i++){let r=t[i];Qt.setFromBufferAttribute(r),this.morphTargetsRelative?(Pt.addVectors(this.boundingBox.min,Qt.min),this.boundingBox.expandByPoint(Pt),Pt.addVectors(this.boundingBox.max,Qt.max),this.boundingBox.expandByPoint(Pt)):(this.boundingBox.expandByPoint(Qt.min),this.boundingBox.expandByPoint(Qt.max))}}else this.boundingBox.makeEmpty();(isNaN(this.boundingBox.min.x)||isNaN(this.boundingBox.min.y)||isNaN(this.boundingBox.min.z))&&console.error('THREE.BufferGeometry.computeBoundingBox(): Computed min/max have NaN values. The "position" attribute is likely to have NaN values.',this)}computeBoundingSphere(){this.boundingSphere===null&&(this.boundingSphere=new ds);let e=this.attributes.position,t=this.morphAttributes.position;if(e&&e.isGLBufferAttribute){console.error("THREE.BufferGeometry.computeBoundingSphere(): GLBufferAttribute requires a manual bounding sphere.",this),this.boundingSphere.set(new N,1/0);return}if(e){let i=this.boundingSphere.center;if(Qt.setFromBufferAttribute(e),t)for(let r=0,a=t.length;r<a;r++){let o=t[r];zs.setFromBufferAttribute(o),this.morphTargetsRelative?(Pt.addVectors(Qt.min,zs.min),Qt.expandByPoint(Pt),Pt.addVectors(Qt.max,zs.max),Qt.expandByPoint(Pt)):(Qt.expandByPoint(zs.min),Qt.expandByPoint(zs.max))}Qt.getCenter(i);let s=0;for(let r=0,a=e.count;r<a;r++)Pt.fromBufferAttribute(e,r),s=Math.max(s,i.distanceToSquared(Pt));if(t)for(let r=0,a=t.length;r<a;r++){let o=t[r],c=this.morphTargetsRelative;for(let l=0,u=o.count;l<u;l++)Pt.fromBufferAttribute(o,l),c&&(is.fromBufferAttribute(e,l),Pt.add(is)),s=Math.max(s,i.distanceToSquared(Pt))}this.boundingSphere.radius=Math.sqrt(s),isNaN(this.boundingSphere.radius)&&console.error('THREE.BufferGeometry.computeBoundingSphere(): Computed radius is NaN. The "position" attribute is likely to have NaN values.',this)}}computeTangents(){let e=this.index,t=this.attributes;if(e===null||t.position===void 0||t.normal===void 0||t.uv===void 0){console.error("THREE.BufferGeometry: .computeTangents() failed. Missing required attributes (index, position, normal or uv)");return}let i=t.position,s=t.normal,r=t.uv;this.hasAttribute("tangent")===!1&&this.setAttribute("tangent",new Nt(new Float32Array(4*i.count),4));let a=this.getAttribute("tangent"),o=[],c=[];for(let D=0;D<i.count;D++)o[D]=new N,c[D]=new N;let l=new N,u=new N,h=new N,d=new de,f=new de,g=new de,x=new N,m=new N;function p(D,b,w){l.fromBufferAttribute(i,D),u.fromBufferAttribute(i,b),h.fromBufferAttribute(i,w),d.fromBufferAttribute(r,D),f.fromBufferAttribute(r,b),g.fromBufferAttribute(r,w),u.sub(l),h.sub(l),f.sub(d),g.sub(d);let C=1/(f.x*g.y-g.x*f.y);isFinite(C)&&(x.copy(u).multiplyScalar(g.y).addScaledVector(h,-f.y).multiplyScalar(C),m.copy(h).multiplyScalar(f.x).addScaledVector(u,-g.x).multiplyScalar(C),o[D].add(x),o[b].add(x),o[w].add(x),c[D].add(m),c[b].add(m),c[w].add(m))}let T=this.groups;T.length===0&&(T=[{start:0,count:e.count}]);for(let D=0,b=T.length;D<b;++D){let w=T[D],C=w.start,k=w.count;for(let G=C,q=C+k;G<q;G+=3)p(e.getX(G+0),e.getX(G+1),e.getX(G+2))}let M=new N,y=new N,R=new N,E=new N;function P(D){R.fromBufferAttribute(s,D),E.copy(R);let b=o[D];M.copy(b),M.sub(R.multiplyScalar(R.dot(b))).normalize(),y.crossVectors(E,b);let C=y.dot(c[D])<0?-1:1;a.setXYZW(D,M.x,M.y,M.z,C)}for(let D=0,b=T.length;D<b;++D){let w=T[D],C=w.start,k=w.count;for(let G=C,q=C+k;G<q;G+=3)P(e.getX(G+0)),P(e.getX(G+1)),P(e.getX(G+2))}}computeVertexNormals(){let e=this.index,t=this.getAttribute("position");if(t!==void 0){let i=this.getAttribute("normal");if(i===void 0)i=new Nt(new Float32Array(t.count*3),3),this.setAttribute("normal",i);else for(let d=0,f=i.count;d<f;d++)i.setXYZ(d,0,0,0);let s=new N,r=new N,a=new N,o=new N,c=new N,l=new N,u=new N,h=new N;if(e)for(let d=0,f=e.count;d<f;d+=3){let g=e.getX(d+0),x=e.getX(d+1),m=e.getX(d+2);s.fromBufferAttribute(t,g),r.fromBufferAttribute(t,x),a.fromBufferAttribute(t,m),u.subVectors(a,r),h.subVectors(s,r),u.cross(h),o.fromBufferAttribute(i,g),c.fromBufferAttribute(i,x),l.fromBufferAttribute(i,m),o.add(u),c.add(u),l.add(u),i.setXYZ(g,o.x,o.y,o.z),i.setXYZ(x,c.x,c.y,c.z),i.setXYZ(m,l.x,l.y,l.z)}else for(let d=0,f=t.count;d<f;d+=3)s.fromBufferAttribute(t,d+0),r.fromBufferAttribute(t,d+1),a.fromBufferAttribute(t,d+2),u.subVectors(a,r),h.subVectors(s,r),u.cross(h),i.setXYZ(d+0,u.x,u.y,u.z),i.setXYZ(d+1,u.x,u.y,u.z),i.setXYZ(d+2,u.x,u.y,u.z);this.normalizeNormals(),i.needsUpdate=!0}}normalizeNormals(){let e=this.attributes.normal;for(let t=0,i=e.count;t<i;t++)Pt.fromBufferAttribute(e,t),Pt.normalize(),e.setXYZ(t,Pt.x,Pt.y,Pt.z)}toNonIndexed(){function e(o,c){let l=o.array,u=o.itemSize,h=o.normalized,d=new l.constructor(c.length*u),f=0,g=0;for(let x=0,m=c.length;x<m;x++){o.isInterleavedBufferAttribute?f=c[x]*o.data.stride+o.offset:f=c[x]*u;for(let p=0;p<u;p++)d[g++]=l[f++]}return new Nt(d,u,h)}if(this.index===null)return console.warn("THREE.BufferGeometry.toNonIndexed(): BufferGeometry is already non-indexed."),this;let t=new n,i=this.index.array,s=this.attributes;for(let o in s){let c=s[o],l=e(c,i);t.setAttribute(o,l)}let r=this.morphAttributes;for(let o in r){let c=[],l=r[o];for(let u=0,h=l.length;u<h;u++){let d=l[u],f=e(d,i);c.push(f)}t.morphAttributes[o]=c}t.morphTargetsRelative=this.morphTargetsRelative;let a=this.groups;for(let o=0,c=a.length;o<c;o++){let l=a[o];t.addGroup(l.start,l.count,l.materialIndex)}return t}toJSON(){let e={metadata:{version:4.7,type:"BufferGeometry",generator:"BufferGeometry.toJSON"}};if(e.uuid=this.uuid,e.type=this.type,this.name!==""&&(e.name=this.name),Object.keys(this.userData).length>0&&(e.userData=this.userData),this.parameters!==void 0){let c=this.parameters;for(let l in c)c[l]!==void 0&&(e[l]=c[l]);return e}e.data={attributes:{}};let t=this.index;t!==null&&(e.data.index={type:t.array.constructor.name,array:Array.prototype.slice.call(t.array)});let i=this.attributes;for(let c in i){let l=i[c];e.data.attributes[c]=l.toJSON(e.data)}let s={},r=!1;for(let c in this.morphAttributes){let l=this.morphAttributes[c],u=[];for(let h=0,d=l.length;h<d;h++){let f=l[h];u.push(f.toJSON(e.data))}u.length>0&&(s[c]=u,r=!0)}r&&(e.data.morphAttributes=s,e.data.morphTargetsRelative=this.morphTargetsRelative);let a=this.groups;a.length>0&&(e.data.groups=JSON.parse(JSON.stringify(a)));let o=this.boundingSphere;return o!==null&&(e.data.boundingSphere=o.toJSON()),e}clone(){return new this.constructor().copy(this)}copy(e){this.index=null,this.attributes={},this.morphAttributes={},this.groups=[],this.boundingBox=null,this.boundingSphere=null;let t={};this.name=e.name;let i=e.index;i!==null&&this.setIndex(i.clone());let s=e.attributes;for(let l in s){let u=s[l];this.setAttribute(l,u.clone(t))}let r=e.morphAttributes;for(let l in r){let u=[],h=r[l];for(let d=0,f=h.length;d<f;d++)u.push(h[d].clone(t));this.morphAttributes[l]=u}this.morphTargetsRelative=e.morphTargetsRelative;let a=e.groups;for(let l=0,u=a.length;l<u;l++){let h=a[l];this.addGroup(h.start,h.count,h.materialIndex)}let o=e.boundingBox;o!==null&&(this.boundingBox=o.clone());let c=e.boundingSphere;return c!==null&&(this.boundingSphere=c.clone()),this.drawRange.start=e.drawRange.start,this.drawRange.count=e.drawRange.count,this.userData=e.userData,this}dispose(){this.dispatchEvent({type:"dispose"})}},Fh=new Mt,bi=new fs,jr=new ds,Oh=new N,Qr=new N,ea=new N,ta=new N,xl=new N,na=new N,kh=new N,ia=new N,Ot=class extends Ft{constructor(e=new cn,t=new js){super(),this.isMesh=!0,this.type="Mesh",this.geometry=e,this.material=t,this.morphTargetDictionary=void 0,this.morphTargetInfluences=void 0,this.count=1,this.updateMorphTargets()}copy(e,t){return super.copy(e,t),e.morphTargetInfluences!==void 0&&(this.morphTargetInfluences=e.morphTargetInfluences.slice()),e.morphTargetDictionary!==void 0&&(this.morphTargetDictionary=Object.assign({},e.morphTargetDictionary)),this.material=Array.isArray(e.material)?e.material.slice():e.material,this.geometry=e.geometry,this}updateMorphTargets(){let t=this.geometry.morphAttributes,i=Object.keys(t);if(i.length>0){let s=t[i[0]];if(s!==void 0){this.morphTargetInfluences=[],this.morphTargetDictionary={};for(let r=0,a=s.length;r<a;r++){let o=s[r].name||String(r);this.morphTargetInfluences.push(0),this.morphTargetDictionary[o]=r}}}}getVertexPosition(e,t){let i=this.geometry,s=i.attributes.position,r=i.morphAttributes.position,a=i.morphTargetsRelative;t.fromBufferAttribute(s,e);let o=this.morphTargetInfluences;if(r&&o){na.set(0,0,0);for(let c=0,l=r.length;c<l;c++){let u=o[c],h=r[c];u!==0&&(xl.fromBufferAttribute(h,e),a?na.addScaledVector(xl,u):na.addScaledVector(xl.sub(t),u))}t.add(na)}return t}raycast(e,t){let i=this.geometry,s=this.material,r=this.matrixWorld;s!==void 0&&(i.boundingSphere===null&&i.computeBoundingSphere(),jr.copy(i.boundingSphere),jr.applyMatrix4(r),bi.copy(e.ray).recast(e.near),!(jr.containsPoint(bi.origin)===!1&&(bi.intersectSphere(jr,Oh)===null||bi.origin.distanceToSquared(Oh)>(e.far-e.near)**2))&&(Fh.copy(r).invert(),bi.copy(e.ray).applyMatrix4(Fh),!(i.boundingBox!==null&&bi.intersectsBox(i.boundingBox)===!1)&&this._computeIntersections(e,t,bi)))}_computeIntersections(e,t,i){let s,r=this.geometry,a=this.material,o=r.index,c=r.attributes.position,l=r.attributes.uv,u=r.attributes.uv1,h=r.attributes.normal,d=r.groups,f=r.drawRange;if(o!==null)if(Array.isArray(a))for(let g=0,x=d.length;g<x;g++){let m=d[g],p=a[m.materialIndex],T=Math.max(m.start,f.start),M=Math.min(o.count,Math.min(m.start+m.count,f.start+f.count));for(let y=T,R=M;y<R;y+=3){let E=o.getX(y),P=o.getX(y+1),D=o.getX(y+2);s=sa(this,p,e,i,l,u,h,E,P,D),s&&(s.faceIndex=Math.floor(y/3),s.face.materialIndex=m.materialIndex,t.push(s))}}else{let g=Math.max(0,f.start),x=Math.min(o.count,f.start+f.count);for(let m=g,p=x;m<p;m+=3){let T=o.getX(m),M=o.getX(m+1),y=o.getX(m+2);s=sa(this,a,e,i,l,u,h,T,M,y),s&&(s.faceIndex=Math.floor(m/3),t.push(s))}}else if(c!==void 0)if(Array.isArray(a))for(let g=0,x=d.length;g<x;g++){let m=d[g],p=a[m.materialIndex],T=Math.max(m.start,f.start),M=Math.min(c.count,Math.min(m.start+m.count,f.start+f.count));for(let y=T,R=M;y<R;y+=3){let E=y,P=y+1,D=y+2;s=sa(this,p,e,i,l,u,h,E,P,D),s&&(s.faceIndex=Math.floor(y/3),s.face.materialIndex=m.materialIndex,t.push(s))}}else{let g=Math.max(0,f.start),x=Math.min(c.count,f.start+f.count);for(let m=g,p=x;m<p;m+=3){let T=m,M=m+1,y=m+2;s=sa(this,a,e,i,l,u,h,T,M,y),s&&(s.faceIndex=Math.floor(m/3),t.push(s))}}}};function tp(n,e,t,i,s,r,a,o){let c;if(e.side===Wt?c=i.intersectTriangle(a,r,s,!0,o):c=i.intersectTriangle(s,r,a,e.side===Wn,o),c===null)return null;ia.copy(o),ia.applyMatrix4(n.matrixWorld);let l=t.ray.origin.distanceTo(ia);return l<t.near||l>t.far?null:{distance:l,point:ia.clone(),object:n}}function sa(n,e,t,i,s,r,a,o,c,l){n.getVertexPosition(o,Qr),n.getVertexPosition(c,ea),n.getVertexPosition(l,ta);let u=tp(n,e,t,i,Qr,ea,ta,kh);if(u){let h=new N;ii.getBarycoord(kh,Qr,ea,ta,h),s&&(u.uv=ii.getInterpolatedAttribute(s,o,c,l,h,new de)),r&&(u.uv1=ii.getInterpolatedAttribute(r,o,c,l,h,new de)),a&&(u.normal=ii.getInterpolatedAttribute(a,o,c,l,h,new N),u.normal.dot(i.direction)>0&&u.normal.multiplyScalar(-1));let d={a:o,b:c,c:l,normal:new N,materialIndex:0};ii.getNormal(Qr,ea,ta,d.normal),u.face=d,u.barycoord=h}return u}var oi=class n extends cn{constructor(e=1,t=1,i=1,s=1,r=1,a=1){super(),this.type="BoxGeometry",this.parameters={width:e,height:t,depth:i,widthSegments:s,heightSegments:r,depthSegments:a};let o=this;s=Math.floor(s),r=Math.floor(r),a=Math.floor(a);let c=[],l=[],u=[],h=[],d=0,f=0;g("z","y","x",-1,-1,i,t,e,a,r,0),g("z","y","x",1,-1,i,t,-e,a,r,1),g("x","z","y",1,1,e,i,t,s,a,2),g("x","z","y",1,-1,e,i,-t,s,a,3),g("x","y","z",1,-1,e,t,i,s,r,4),g("x","y","z",-1,-1,e,t,-i,s,r,5),this.setIndex(c),this.setAttribute("position",new Gt(l,3)),this.setAttribute("normal",new Gt(u,3)),this.setAttribute("uv",new Gt(h,2));function g(x,m,p,T,M,y,R,E,P,D,b){let w=y/P,C=R/D,k=y/2,G=R/2,q=E/2,X=P+1,V=D+1,te=0,U=0,Q=new N;for(let he=0;he<V;he++){let ue=he*C-G;for(let ze=0;ze<X;ze++){let je=ze*w-k;Q[x]=je*T,Q[m]=ue*M,Q[p]=q,l.push(Q.x,Q.y,Q.z),Q[x]=0,Q[m]=0,Q[p]=E>0?1:-1,u.push(Q.x,Q.y,Q.z),h.push(ze/P),h.push(1-he/D),te+=1}}for(let he=0;he<D;he++)for(let ue=0;ue<P;ue++){let ze=d+ue+X*he,je=d+ue+X*(he+1),Qe=d+(ue+1)+X*(he+1),it=d+(ue+1)+X*he;c.push(ze,je,it),c.push(je,Qe,it),U+=6}o.addGroup(f,U,b),f+=U,d+=te}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new n(e.width,e.height,e.depth,e.widthSegments,e.heightSegments,e.depthSegments)}};function Oi(n){let e={};for(let t in n){e[t]={};for(let i in n[t]){let s=n[t][i];s&&(s.isColor||s.isMatrix3||s.isMatrix4||s.isVector2||s.isVector3||s.isVector4||s.isTexture||s.isQuaternion)?s.isRenderTargetTexture?(console.warn("UniformsUtils: Textures of render targets cannot be cloned via cloneUniforms() or mergeUniforms()."),e[t][i]=null):e[t][i]=s.clone():Array.isArray(s)?e[t][i]=s.slice():e[t][i]=s}}return e}function kt(n){let e={};for(let t=0;t<n.length;t++){let i=Oi(n[t]);for(let s in i)e[s]=i[s]}return e}function np(n){let e=[];for(let t=0;t<n.length;t++)e.push(n[t].clone());return e}function rc(n){let e=n.getRenderTarget();return e===null?n.outputColorSpace:e.isXRRenderTarget===!0?e.texture.colorSpace:st.workingColorSpace}var Fu={clone:Oi,merge:kt},ip=`void main() {
	gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
}`,sp=`void main() {
	gl_FragColor = vec4( 1.0, 0.0, 0.0, 1.0 );
}`,xn=class extends ai{constructor(e){super(),this.isShaderMaterial=!0,this.type="ShaderMaterial",this.defines={},this.uniforms={},this.uniformsGroups=[],this.vertexShader=ip,this.fragmentShader=sp,this.linewidth=1,this.wireframe=!1,this.wireframeLinewidth=1,this.fog=!1,this.lights=!1,this.clipping=!1,this.forceSinglePass=!0,this.extensions={clipCullDistance:!1,multiDraw:!1},this.defaultAttributeValues={color:[1,1,1],uv:[0,0],uv1:[0,0]},this.index0AttributeName=void 0,this.uniformsNeedUpdate=!1,this.glslVersion=null,e!==void 0&&this.setValues(e)}copy(e){return super.copy(e),this.fragmentShader=e.fragmentShader,this.vertexShader=e.vertexShader,this.uniforms=Oi(e.uniforms),this.uniformsGroups=np(e.uniformsGroups),this.defines=Object.assign({},e.defines),this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.fog=e.fog,this.lights=e.lights,this.clipping=e.clipping,this.extensions=Object.assign({},e.extensions),this.glslVersion=e.glslVersion,this}toJSON(e){let t=super.toJSON(e);t.glslVersion=this.glslVersion,t.uniforms={};for(let s in this.uniforms){let a=this.uniforms[s].value;a&&a.isTexture?t.uniforms[s]={type:"t",value:a.toJSON(e).uuid}:a&&a.isColor?t.uniforms[s]={type:"c",value:a.getHex()}:a&&a.isVector2?t.uniforms[s]={type:"v2",value:a.toArray()}:a&&a.isVector3?t.uniforms[s]={type:"v3",value:a.toArray()}:a&&a.isVector4?t.uniforms[s]={type:"v4",value:a.toArray()}:a&&a.isMatrix3?t.uniforms[s]={type:"m3",value:a.toArray()}:a&&a.isMatrix4?t.uniforms[s]={type:"m4",value:a.toArray()}:t.uniforms[s]={value:a}}Object.keys(this.defines).length>0&&(t.defines=this.defines),t.vertexShader=this.vertexShader,t.fragmentShader=this.fragmentShader,t.lights=this.lights,t.clipping=this.clipping;let i={};for(let s in this.extensions)this.extensions[s]===!0&&(i[s]=!0);return Object.keys(i).length>0&&(t.extensions=i),t}},tr=class extends Ft{constructor(){super(),this.isCamera=!0,this.type="Camera",this.matrixWorldInverse=new Mt,this.projectionMatrix=new Mt,this.projectionMatrixInverse=new Mt,this.coordinateSystem=mn,this._reversedDepth=!1}get reversedDepth(){return this._reversedDepth}copy(e,t){return super.copy(e,t),this.matrixWorldInverse.copy(e.matrixWorldInverse),this.projectionMatrix.copy(e.projectionMatrix),this.projectionMatrixInverse.copy(e.projectionMatrixInverse),this.coordinateSystem=e.coordinateSystem,this}getWorldDirection(e){return super.getWorldDirection(e).negate()}updateMatrixWorld(e){super.updateMatrixWorld(e),this.matrixWorldInverse.copy(this.matrixWorld).invert()}updateWorldMatrix(e,t){super.updateWorldMatrix(e,t),this.matrixWorldInverse.copy(this.matrixWorld).invert()}clone(){return new this.constructor().copy(this)}},ni=new N,Bh=new de,zh=new de,Ut=class extends tr{constructor(e=50,t=1,i=.1,s=2e3){super(),this.isPerspectiveCamera=!0,this.type="PerspectiveCamera",this.fov=e,this.zoom=1,this.near=i,this.far=s,this.focus=10,this.aspect=t,this.view=null,this.filmGauge=35,this.filmOffset=0,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.fov=e.fov,this.zoom=e.zoom,this.near=e.near,this.far=e.far,this.focus=e.focus,this.aspect=e.aspect,this.view=e.view===null?null:Object.assign({},e.view),this.filmGauge=e.filmGauge,this.filmOffset=e.filmOffset,this}setFocalLength(e){let t=.5*this.getFilmHeight()/e;this.fov=cs*2*Math.atan(t),this.updateProjectionMatrix()}getFocalLength(){let e=Math.tan(Hs*.5*this.fov);return .5*this.getFilmHeight()/e}getEffectiveFOV(){return cs*2*Math.atan(Math.tan(Hs*.5*this.fov)/this.zoom)}getFilmWidth(){return this.filmGauge*Math.min(this.aspect,1)}getFilmHeight(){return this.filmGauge/Math.max(this.aspect,1)}getViewBounds(e,t,i){ni.set(-1,-1,.5).applyMatrix4(this.projectionMatrixInverse),t.set(ni.x,ni.y).multiplyScalar(-e/ni.z),ni.set(1,1,.5).applyMatrix4(this.projectionMatrixInverse),i.set(ni.x,ni.y).multiplyScalar(-e/ni.z)}getViewSize(e,t){return this.getViewBounds(e,Bh,zh),t.subVectors(zh,Bh)}setViewOffset(e,t,i,s,r,a){this.aspect=e/t,this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=i,this.view.offsetY=s,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=this.near,t=e*Math.tan(Hs*.5*this.fov)/this.zoom,i=2*t,s=this.aspect*i,r=-.5*s,a=this.view;if(this.view!==null&&this.view.enabled){let c=a.fullWidth,l=a.fullHeight;r+=a.offsetX*s/c,t-=a.offsetY*i/l,s*=a.width/c,i*=a.height/l}let o=this.filmOffset;o!==0&&(r+=e*o/this.getFilmWidth()),this.projectionMatrix.makePerspective(r,r+s,t,t-i,e,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.fov=this.fov,t.object.zoom=this.zoom,t.object.near=this.near,t.object.far=this.far,t.object.focus=this.focus,t.object.aspect=this.aspect,this.view!==null&&(t.object.view=Object.assign({},this.view)),t.object.filmGauge=this.filmGauge,t.object.filmOffset=this.filmOffset,t}},ss=-90,rs=1,va=class extends Ft{constructor(e,t,i){super(),this.type="CubeCamera",this.renderTarget=i,this.coordinateSystem=null,this.activeMipmapLevel=0;let s=new Ut(ss,rs,e,t);s.layers=this.layers,this.add(s);let r=new Ut(ss,rs,e,t);r.layers=this.layers,this.add(r);let a=new Ut(ss,rs,e,t);a.layers=this.layers,this.add(a);let o=new Ut(ss,rs,e,t);o.layers=this.layers,this.add(o);let c=new Ut(ss,rs,e,t);c.layers=this.layers,this.add(c);let l=new Ut(ss,rs,e,t);l.layers=this.layers,this.add(l)}updateCoordinateSystem(){let e=this.coordinateSystem,t=this.children.concat(),[i,s,r,a,o,c]=t;for(let l of t)this.remove(l);if(e===mn)i.up.set(0,1,0),i.lookAt(1,0,0),s.up.set(0,1,0),s.lookAt(-1,0,0),r.up.set(0,0,-1),r.lookAt(0,1,0),a.up.set(0,0,1),a.lookAt(0,-1,0),o.up.set(0,1,0),o.lookAt(0,0,1),c.up.set(0,1,0),c.lookAt(0,0,-1);else if(e===$s)i.up.set(0,-1,0),i.lookAt(-1,0,0),s.up.set(0,-1,0),s.lookAt(1,0,0),r.up.set(0,0,1),r.lookAt(0,1,0),a.up.set(0,0,-1),a.lookAt(0,-1,0),o.up.set(0,-1,0),o.lookAt(0,0,1),c.up.set(0,-1,0),c.lookAt(0,0,-1);else throw new Error("THREE.CubeCamera.updateCoordinateSystem(): Invalid coordinate system: "+e);for(let l of t)this.add(l),l.updateMatrixWorld()}update(e,t){this.parent===null&&this.updateMatrixWorld();let{renderTarget:i,activeMipmapLevel:s}=this;this.coordinateSystem!==e.coordinateSystem&&(this.coordinateSystem=e.coordinateSystem,this.updateCoordinateSystem());let[r,a,o,c,l,u]=this.children,h=e.getRenderTarget(),d=e.getActiveCubeFace(),f=e.getActiveMipmapLevel(),g=e.xr.enabled;e.xr.enabled=!1;let x=i.texture.generateMipmaps;i.texture.generateMipmaps=!1,e.setRenderTarget(i,0,s),e.render(t,r),e.setRenderTarget(i,1,s),e.render(t,a),e.setRenderTarget(i,2,s),e.render(t,o),e.setRenderTarget(i,3,s),e.render(t,c),e.setRenderTarget(i,4,s),e.render(t,l),i.texture.generateMipmaps=x,e.setRenderTarget(i,5,s),e.render(t,u),e.setRenderTarget(h,d,f),e.xr.enabled=g,i.texture.needsPMREMUpdate=!0}},nr=class extends Yt{constructor(e=[],t=Li,i,s,r,a,o,c,l,u){super(e,t,i,s,r,a,o,c,l,u),this.isCubeTexture=!0,this.flipY=!1}get images(){return this.image}set images(e){this.image=e}},ya=class extends Sn{constructor(e=1,t={}){super(e,e,t),this.isWebGLCubeRenderTarget=!0;let i={width:e,height:e,depth:1},s=[i,i,i,i,i,i];this.texture=new nr(s),this._setTextureOptions(t),this.texture.isRenderTargetTexture=!0}fromEquirectangularTexture(e,t){this.texture.type=t.type,this.texture.colorSpace=t.colorSpace,this.texture.generateMipmaps=t.generateMipmaps,this.texture.minFilter=t.minFilter,this.texture.magFilter=t.magFilter;let i={uniforms:{tEquirect:{value:null}},vertexShader:`

				varying vec3 vWorldDirection;

				vec3 transformDirection( in vec3 dir, in mat4 matrix ) {

					return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );

				}

				void main() {

					vWorldDirection = transformDirection( position, modelMatrix );

					#include <begin_vertex>
					#include <project_vertex>

				}
			`,fragmentShader:`

				uniform sampler2D tEquirect;

				varying vec3 vWorldDirection;

				#include <common>

				void main() {

					vec3 direction = normalize( vWorldDirection );

					vec2 sampleUV = equirectUv( direction );

					gl_FragColor = texture2D( tEquirect, sampleUV );

				}
			`},s=new oi(5,5,5),r=new xn({name:"CubemapFromEquirect",uniforms:Oi(i.uniforms),vertexShader:i.vertexShader,fragmentShader:i.fragmentShader,side:Wt,blending:Xn});r.uniforms.tEquirect.value=t;let a=new Ot(s,r),o=t.minFilter;return t.minFilter===pi&&(t.minFilter=gn),new va(1,10,this).update(e,a),t.minFilter=o,a.geometry.dispose(),a.material.dispose(),this}clear(e,t=!0,i=!0,s=!0){let r=e.getRenderTarget();for(let a=0;a<6;a++)e.setRenderTarget(this,a),e.clear(t,i,s);e.setRenderTarget(r)}},Ti=class extends Ft{constructor(){super(),this.isGroup=!0,this.type="Group"}},rp={type:"move"},ps=class{constructor(){this._targetRay=null,this._grip=null,this._hand=null}getHandSpace(){return this._hand===null&&(this._hand=new Ti,this._hand.matrixAutoUpdate=!1,this._hand.visible=!1,this._hand.joints={},this._hand.inputState={pinching:!1}),this._hand}getTargetRaySpace(){return this._targetRay===null&&(this._targetRay=new Ti,this._targetRay.matrixAutoUpdate=!1,this._targetRay.visible=!1,this._targetRay.hasLinearVelocity=!1,this._targetRay.linearVelocity=new N,this._targetRay.hasAngularVelocity=!1,this._targetRay.angularVelocity=new N),this._targetRay}getGripSpace(){return this._grip===null&&(this._grip=new Ti,this._grip.matrixAutoUpdate=!1,this._grip.visible=!1,this._grip.hasLinearVelocity=!1,this._grip.linearVelocity=new N,this._grip.hasAngularVelocity=!1,this._grip.angularVelocity=new N),this._grip}dispatchEvent(e){return this._targetRay!==null&&this._targetRay.dispatchEvent(e),this._grip!==null&&this._grip.dispatchEvent(e),this._hand!==null&&this._hand.dispatchEvent(e),this}connect(e){if(e&&e.hand){let t=this._hand;if(t)for(let i of e.hand.values())this._getHandJoint(t,i)}return this.dispatchEvent({type:"connected",data:e}),this}disconnect(e){return this.dispatchEvent({type:"disconnected",data:e}),this._targetRay!==null&&(this._targetRay.visible=!1),this._grip!==null&&(this._grip.visible=!1),this._hand!==null&&(this._hand.visible=!1),this}update(e,t,i){let s=null,r=null,a=null,o=this._targetRay,c=this._grip,l=this._hand;if(e&&t.session.visibilityState!=="visible-blurred"){if(l&&e.hand){a=!0;for(let x of e.hand.values()){let m=t.getJointPose(x,i),p=this._getHandJoint(l,x);m!==null&&(p.matrix.fromArray(m.transform.matrix),p.matrix.decompose(p.position,p.rotation,p.scale),p.matrixWorldNeedsUpdate=!0,p.jointRadius=m.radius),p.visible=m!==null}let u=l.joints["index-finger-tip"],h=l.joints["thumb-tip"],d=u.position.distanceTo(h.position),f=.02,g=.005;l.inputState.pinching&&d>f+g?(l.inputState.pinching=!1,this.dispatchEvent({type:"pinchend",handedness:e.handedness,target:this})):!l.inputState.pinching&&d<=f-g&&(l.inputState.pinching=!0,this.dispatchEvent({type:"pinchstart",handedness:e.handedness,target:this}))}else c!==null&&e.gripSpace&&(r=t.getPose(e.gripSpace,i),r!==null&&(c.matrix.fromArray(r.transform.matrix),c.matrix.decompose(c.position,c.rotation,c.scale),c.matrixWorldNeedsUpdate=!0,r.linearVelocity?(c.hasLinearVelocity=!0,c.linearVelocity.copy(r.linearVelocity)):c.hasLinearVelocity=!1,r.angularVelocity?(c.hasAngularVelocity=!0,c.angularVelocity.copy(r.angularVelocity)):c.hasAngularVelocity=!1));o!==null&&(s=t.getPose(e.targetRaySpace,i),s===null&&r!==null&&(s=r),s!==null&&(o.matrix.fromArray(s.transform.matrix),o.matrix.decompose(o.position,o.rotation,o.scale),o.matrixWorldNeedsUpdate=!0,s.linearVelocity?(o.hasLinearVelocity=!0,o.linearVelocity.copy(s.linearVelocity)):o.hasLinearVelocity=!1,s.angularVelocity?(o.hasAngularVelocity=!0,o.angularVelocity.copy(s.angularVelocity)):o.hasAngularVelocity=!1,this.dispatchEvent(rp)))}return o!==null&&(o.visible=s!==null),c!==null&&(c.visible=r!==null),l!==null&&(l.visible=a!==null),this}_getHandJoint(e,t){if(e.joints[t.jointName]===void 0){let i=new Ti;i.matrixAutoUpdate=!1,i.visible=!1,e.joints[t.jointName]=i,e.add(i)}return e.joints[t.jointName]}};var ir=class extends Ft{constructor(){super(),this.isScene=!0,this.type="Scene",this.background=null,this.environment=null,this.fog=null,this.backgroundBlurriness=0,this.backgroundIntensity=1,this.backgroundRotation=new _n,this.environmentIntensity=1,this.environmentRotation=new _n,this.overrideMaterial=null,typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}copy(e,t){return super.copy(e,t),e.background!==null&&(this.background=e.background.clone()),e.environment!==null&&(this.environment=e.environment.clone()),e.fog!==null&&(this.fog=e.fog.clone()),this.backgroundBlurriness=e.backgroundBlurriness,this.backgroundIntensity=e.backgroundIntensity,this.backgroundRotation.copy(e.backgroundRotation),this.environmentIntensity=e.environmentIntensity,this.environmentRotation.copy(e.environmentRotation),e.overrideMaterial!==null&&(this.overrideMaterial=e.overrideMaterial.clone()),this.matrixAutoUpdate=e.matrixAutoUpdate,this}toJSON(e){let t=super.toJSON(e);return this.fog!==null&&(t.object.fog=this.fog.toJSON()),this.backgroundBlurriness>0&&(t.object.backgroundBlurriness=this.backgroundBlurriness),this.backgroundIntensity!==1&&(t.object.backgroundIntensity=this.backgroundIntensity),t.object.backgroundRotation=this.backgroundRotation.toArray(),this.environmentIntensity!==1&&(t.object.environmentIntensity=this.environmentIntensity),t.object.environmentRotation=this.environmentRotation.toArray(),t}};var vl=new N,ap=new N,op=new $e,an=class{constructor(e=new N(1,0,0),t=0){this.isPlane=!0,this.normal=e,this.constant=t}set(e,t){return this.normal.copy(e),this.constant=t,this}setComponents(e,t,i,s){return this.normal.set(e,t,i),this.constant=s,this}setFromNormalAndCoplanarPoint(e,t){return this.normal.copy(e),this.constant=-t.dot(this.normal),this}setFromCoplanarPoints(e,t,i){let s=vl.subVectors(i,t).cross(ap.subVectors(e,t)).normalize();return this.setFromNormalAndCoplanarPoint(s,e),this}copy(e){return this.normal.copy(e.normal),this.constant=e.constant,this}normalize(){let e=1/this.normal.length();return this.normal.multiplyScalar(e),this.constant*=e,this}negate(){return this.constant*=-1,this.normal.negate(),this}distanceToPoint(e){return this.normal.dot(e)+this.constant}distanceToSphere(e){return this.distanceToPoint(e.center)-e.radius}projectPoint(e,t){return t.copy(e).addScaledVector(this.normal,-this.distanceToPoint(e))}intersectLine(e,t){let i=e.delta(vl),s=this.normal.dot(i);if(s===0)return this.distanceToPoint(e.start)===0?t.copy(e.start):null;let r=-(e.start.dot(this.normal)+this.constant)/s;return r<0||r>1?null:t.copy(e.start).addScaledVector(i,r)}intersectsLine(e){let t=this.distanceToPoint(e.start),i=this.distanceToPoint(e.end);return t<0&&i>0||i<0&&t>0}intersectsBox(e){return e.intersectsPlane(this)}intersectsSphere(e){return e.intersectsPlane(this)}coplanarPoint(e){return e.copy(this.normal).multiplyScalar(-this.constant)}applyMatrix4(e,t){let i=t||op.getNormalMatrix(e),s=this.coplanarPoint(vl).applyMatrix4(e),r=this.normal.applyMatrix3(i).normalize();return this.constant=-s.dot(r),this}translate(e){return this.constant-=e.dot(this.normal),this}equals(e){return e.normal.equals(this.normal)&&e.constant===this.constant}clone(){return new this.constructor().copy(this)}},Mi=new ds,lp=new de(.5,.5),ra=new N,ms=class{constructor(e=new an,t=new an,i=new an,s=new an,r=new an,a=new an){this.planes=[e,t,i,s,r,a]}set(e,t,i,s,r,a){let o=this.planes;return o[0].copy(e),o[1].copy(t),o[2].copy(i),o[3].copy(s),o[4].copy(r),o[5].copy(a),this}copy(e){let t=this.planes;for(let i=0;i<6;i++)t[i].copy(e.planes[i]);return this}setFromProjectionMatrix(e,t=mn,i=!1){let s=this.planes,r=e.elements,a=r[0],o=r[1],c=r[2],l=r[3],u=r[4],h=r[5],d=r[6],f=r[7],g=r[8],x=r[9],m=r[10],p=r[11],T=r[12],M=r[13],y=r[14],R=r[15];if(s[0].setComponents(l-a,f-u,p-g,R-T).normalize(),s[1].setComponents(l+a,f+u,p+g,R+T).normalize(),s[2].setComponents(l+o,f+h,p+x,R+M).normalize(),s[3].setComponents(l-o,f-h,p-x,R-M).normalize(),i)s[4].setComponents(c,d,m,y).normalize(),s[5].setComponents(l-c,f-d,p-m,R-y).normalize();else if(s[4].setComponents(l-c,f-d,p-m,R-y).normalize(),t===mn)s[5].setComponents(l+c,f+d,p+m,R+y).normalize();else if(t===$s)s[5].setComponents(c,d,m,y).normalize();else throw new Error("THREE.Frustum.setFromProjectionMatrix(): Invalid coordinate system: "+t);return this}intersectsObject(e){if(e.boundingSphere!==void 0)e.boundingSphere===null&&e.computeBoundingSphere(),Mi.copy(e.boundingSphere).applyMatrix4(e.matrixWorld);else{let t=e.geometry;t.boundingSphere===null&&t.computeBoundingSphere(),Mi.copy(t.boundingSphere).applyMatrix4(e.matrixWorld)}return this.intersectsSphere(Mi)}intersectsSprite(e){Mi.center.set(0,0,0);let t=lp.distanceTo(e.center);return Mi.radius=.7071067811865476+t,Mi.applyMatrix4(e.matrixWorld),this.intersectsSphere(Mi)}intersectsSphere(e){let t=this.planes,i=e.center,s=-e.radius;for(let r=0;r<6;r++)if(t[r].distanceToPoint(i)<s)return!1;return!0}intersectsBox(e){let t=this.planes;for(let i=0;i<6;i++){let s=t[i];if(ra.x=s.normal.x>0?e.max.x:e.min.x,ra.y=s.normal.y>0?e.max.y:e.min.y,ra.z=s.normal.z>0?e.max.z:e.min.z,s.distanceToPoint(ra)<0)return!1}return!0}containsPoint(e){let t=this.planes;for(let i=0;i<6;i++)if(t[i].distanceToPoint(e)<0)return!1;return!0}clone(){return new this.constructor().copy(this)}};var sr=class extends Yt{constructor(e,t,i,s,r,a,o,c,l){super(e,t,i,s,r,a,o,c,l),this.isCanvasTexture=!0,this.needsUpdate=!0}},rr=class extends Yt{constructor(e,t,i=mi,s,r,a,o=on,c=on,l,u=ls,h=1){if(u!==ls&&u!==bs)throw new Error("DepthTexture format must be either THREE.DepthFormat or THREE.DepthStencilFormat");let d={width:e,height:t,depth:h};super(d,s,r,a,o,c,u,i,l),this.isDepthTexture=!0,this.flipY=!1,this.generateMipmaps=!1,this.compareFunction=null}copy(e){return super.copy(e),this.source=new us(Object.assign({},e.image)),this.compareFunction=e.compareFunction,this}toJSON(e){let t=super.toJSON(e);return this.compareFunction!==null&&(t.compareFunction=this.compareFunction),t}},ar=class extends Yt{constructor(e=null){super(),this.sourceTexture=e,this.isExternalTexture=!0}copy(e){return super.copy(e),this.sourceTexture=e.sourceTexture,this}};var en=class{constructor(){this.type="Curve",this.arcLengthDivisions=200,this.needsUpdate=!1,this.cacheArcLengths=null}getPoint(){console.warn("THREE.Curve: .getPoint() not implemented.")}getPointAt(e,t){let i=this.getUtoTmapping(e);return this.getPoint(i,t)}getPoints(e=5){let t=[];for(let i=0;i<=e;i++)t.push(this.getPoint(i/e));return t}getSpacedPoints(e=5){let t=[];for(let i=0;i<=e;i++)t.push(this.getPointAt(i/e));return t}getLength(){let e=this.getLengths();return e[e.length-1]}getLengths(e=this.arcLengthDivisions){if(this.cacheArcLengths&&this.cacheArcLengths.length===e+1&&!this.needsUpdate)return this.cacheArcLengths;this.needsUpdate=!1;let t=[],i,s=this.getPoint(0),r=0;t.push(0);for(let a=1;a<=e;a++)i=this.getPoint(a/e),r+=i.distanceTo(s),t.push(r),s=i;return this.cacheArcLengths=t,t}updateArcLengths(){this.needsUpdate=!0,this.getLengths()}getUtoTmapping(e,t=null){let i=this.getLengths(),s=0,r=i.length,a;t?a=t:a=e*i[r-1];let o=0,c=r-1,l;for(;o<=c;)if(s=Math.floor(o+(c-o)/2),l=i[s]-a,l<0)o=s+1;else if(l>0)c=s-1;else{c=s;break}if(s=c,i[s]===a)return s/(r-1);let u=i[s],d=i[s+1]-u,f=(a-u)/d;return(s+f)/(r-1)}getTangent(e,t){let s=e-1e-4,r=e+1e-4;s<0&&(s=0),r>1&&(r=1);let a=this.getPoint(s),o=this.getPoint(r),c=t||(a.isVector2?new de:new N);return c.copy(o).sub(a).normalize(),c}getTangentAt(e,t){let i=this.getUtoTmapping(e);return this.getTangent(i,t)}computeFrenetFrames(e,t=!1){let i=new N,s=[],r=[],a=[],o=new N,c=new Mt;for(let f=0;f<=e;f++){let g=f/e;s[f]=this.getTangentAt(g,new N)}r[0]=new N,a[0]=new N;let l=Number.MAX_VALUE,u=Math.abs(s[0].x),h=Math.abs(s[0].y),d=Math.abs(s[0].z);u<=l&&(l=u,i.set(1,0,0)),h<=l&&(l=h,i.set(0,1,0)),d<=l&&i.set(0,0,1),o.crossVectors(s[0],i).normalize(),r[0].crossVectors(s[0],o),a[0].crossVectors(s[0],r[0]);for(let f=1;f<=e;f++){if(r[f]=r[f-1].clone(),a[f]=a[f-1].clone(),o.crossVectors(s[f-1],s[f]),o.length()>Number.EPSILON){o.normalize();let g=Math.acos(Je(s[f-1].dot(s[f]),-1,1));r[f].applyMatrix4(c.makeRotationAxis(o,g))}a[f].crossVectors(s[f],r[f])}if(t===!0){let f=Math.acos(Je(r[0].dot(r[e]),-1,1));f/=e,s[0].dot(o.crossVectors(r[0],r[e]))>0&&(f=-f);for(let g=1;g<=e;g++)r[g].applyMatrix4(c.makeRotationAxis(s[g],f*g)),a[g].crossVectors(s[g],r[g])}return{tangents:s,normals:r,binormals:a}}clone(){return new this.constructor().copy(this)}copy(e){return this.arcLengthDivisions=e.arcLengthDivisions,this}toJSON(){let e={metadata:{version:4.7,type:"Curve",generator:"Curve.toJSON"}};return e.arcLengthDivisions=this.arcLengthDivisions,e.type=this.type,e}fromJSON(e){return this.arcLengthDivisions=e.arcLengthDivisions,this}},gs=class extends en{constructor(e=0,t=0,i=1,s=1,r=0,a=Math.PI*2,o=!1,c=0){super(),this.isEllipseCurve=!0,this.type="EllipseCurve",this.aX=e,this.aY=t,this.xRadius=i,this.yRadius=s,this.aStartAngle=r,this.aEndAngle=a,this.aClockwise=o,this.aRotation=c}getPoint(e,t=new de){let i=t,s=Math.PI*2,r=this.aEndAngle-this.aStartAngle,a=Math.abs(r)<Number.EPSILON;for(;r<0;)r+=s;for(;r>s;)r-=s;r<Number.EPSILON&&(a?r=0:r=s),this.aClockwise===!0&&!a&&(r===s?r=-s:r=r-s);let o=this.aStartAngle+e*r,c=this.aX+this.xRadius*Math.cos(o),l=this.aY+this.yRadius*Math.sin(o);if(this.aRotation!==0){let u=Math.cos(this.aRotation),h=Math.sin(this.aRotation),d=c-this.aX,f=l-this.aY;c=d*u-f*h+this.aX,l=d*h+f*u+this.aY}return i.set(c,l)}copy(e){return super.copy(e),this.aX=e.aX,this.aY=e.aY,this.xRadius=e.xRadius,this.yRadius=e.yRadius,this.aStartAngle=e.aStartAngle,this.aEndAngle=e.aEndAngle,this.aClockwise=e.aClockwise,this.aRotation=e.aRotation,this}toJSON(){let e=super.toJSON();return e.aX=this.aX,e.aY=this.aY,e.xRadius=this.xRadius,e.yRadius=this.yRadius,e.aStartAngle=this.aStartAngle,e.aEndAngle=this.aEndAngle,e.aClockwise=this.aClockwise,e.aRotation=this.aRotation,e}fromJSON(e){return super.fromJSON(e),this.aX=e.aX,this.aY=e.aY,this.xRadius=e.xRadius,this.yRadius=e.yRadius,this.aStartAngle=e.aStartAngle,this.aEndAngle=e.aEndAngle,this.aClockwise=e.aClockwise,this.aRotation=e.aRotation,this}},wa=class extends gs{constructor(e,t,i,s,r,a){super(e,t,i,i,s,r,a),this.isArcCurve=!0,this.type="ArcCurve"}};function ac(){let n=0,e=0,t=0,i=0;function s(r,a,o,c){n=r,e=o,t=-3*r+3*a-2*o-c,i=2*r-2*a+o+c}return{initCatmullRom:function(r,a,o,c,l){s(a,o,l*(o-r),l*(c-a))},initNonuniformCatmullRom:function(r,a,o,c,l,u,h){let d=(a-r)/l-(o-r)/(l+u)+(o-a)/u,f=(o-a)/u-(c-a)/(u+h)+(c-o)/h;d*=u,f*=u,s(a,o,d,f)},calc:function(r){let a=r*r,o=a*r;return n+e*r+t*a+i*o}}}var aa=new N,yl=new ac,wl=new ac,bl=new ac,ba=class extends en{constructor(e=[],t=!1,i="centripetal",s=.5){super(),this.isCatmullRomCurve3=!0,this.type="CatmullRomCurve3",this.points=e,this.closed=t,this.curveType=i,this.tension=s}getPoint(e,t=new N){let i=t,s=this.points,r=s.length,a=(r-(this.closed?0:1))*e,o=Math.floor(a),c=a-o;this.closed?o+=o>0?0:(Math.floor(Math.abs(o)/r)+1)*r:c===0&&o===r-1&&(o=r-2,c=1);let l,u;this.closed||o>0?l=s[(o-1)%r]:(aa.subVectors(s[0],s[1]).add(s[0]),l=aa);let h=s[o%r],d=s[(o+1)%r];if(this.closed||o+2<r?u=s[(o+2)%r]:(aa.subVectors(s[r-1],s[r-2]).add(s[r-1]),u=aa),this.curveType==="centripetal"||this.curveType==="chordal"){let f=this.curveType==="chordal"?.5:.25,g=Math.pow(l.distanceToSquared(h),f),x=Math.pow(h.distanceToSquared(d),f),m=Math.pow(d.distanceToSquared(u),f);x<1e-4&&(x=1),g<1e-4&&(g=x),m<1e-4&&(m=x),yl.initNonuniformCatmullRom(l.x,h.x,d.x,u.x,g,x,m),wl.initNonuniformCatmullRom(l.y,h.y,d.y,u.y,g,x,m),bl.initNonuniformCatmullRom(l.z,h.z,d.z,u.z,g,x,m)}else this.curveType==="catmullrom"&&(yl.initCatmullRom(l.x,h.x,d.x,u.x,this.tension),wl.initCatmullRom(l.y,h.y,d.y,u.y,this.tension),bl.initCatmullRom(l.z,h.z,d.z,u.z,this.tension));return i.set(yl.calc(c),wl.calc(c),bl.calc(c)),i}copy(e){super.copy(e),this.points=[];for(let t=0,i=e.points.length;t<i;t++){let s=e.points[t];this.points.push(s.clone())}return this.closed=e.closed,this.curveType=e.curveType,this.tension=e.tension,this}toJSON(){let e=super.toJSON();e.points=[];for(let t=0,i=this.points.length;t<i;t++){let s=this.points[t];e.points.push(s.toArray())}return e.closed=this.closed,e.curveType=this.curveType,e.tension=this.tension,e}fromJSON(e){super.fromJSON(e),this.points=[];for(let t=0,i=e.points.length;t<i;t++){let s=e.points[t];this.points.push(new N().fromArray(s))}return this.closed=e.closed,this.curveType=e.curveType,this.tension=e.tension,this}};function Vh(n,e,t,i,s){let r=(i-e)*.5,a=(s-t)*.5,o=n*n,c=n*o;return(2*t-2*i+r+a)*c+(-3*t+3*i-2*r-a)*o+r*n+t}function cp(n,e){let t=1-n;return t*t*e}function hp(n,e){return 2*(1-n)*n*e}function up(n,e){return n*n*e}function Ws(n,e,t,i){return cp(n,e)+hp(n,t)+up(n,i)}function dp(n,e){let t=1-n;return t*t*t*e}function fp(n,e){let t=1-n;return 3*t*t*n*e}function pp(n,e){return 3*(1-n)*n*n*e}function mp(n,e){return n*n*n*e}function Xs(n,e,t,i,s){return dp(n,e)+fp(n,t)+pp(n,i)+mp(n,s)}var or=class extends en{constructor(e=new de,t=new de,i=new de,s=new de){super(),this.isCubicBezierCurve=!0,this.type="CubicBezierCurve",this.v0=e,this.v1=t,this.v2=i,this.v3=s}getPoint(e,t=new de){let i=t,s=this.v0,r=this.v1,a=this.v2,o=this.v3;return i.set(Xs(e,s.x,r.x,a.x,o.x),Xs(e,s.y,r.y,a.y,o.y)),i}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this.v3.copy(e.v3),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e.v3=this.v3.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this.v3.fromArray(e.v3),this}},Ma=class extends en{constructor(e=new N,t=new N,i=new N,s=new N){super(),this.isCubicBezierCurve3=!0,this.type="CubicBezierCurve3",this.v0=e,this.v1=t,this.v2=i,this.v3=s}getPoint(e,t=new N){let i=t,s=this.v0,r=this.v1,a=this.v2,o=this.v3;return i.set(Xs(e,s.x,r.x,a.x,o.x),Xs(e,s.y,r.y,a.y,o.y),Xs(e,s.z,r.z,a.z,o.z)),i}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this.v3.copy(e.v3),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e.v3=this.v3.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this.v3.fromArray(e.v3),this}},lr=class extends en{constructor(e=new de,t=new de){super(),this.isLineCurve=!0,this.type="LineCurve",this.v1=e,this.v2=t}getPoint(e,t=new de){let i=t;return e===1?i.copy(this.v2):(i.copy(this.v2).sub(this.v1),i.multiplyScalar(e).add(this.v1)),i}getPointAt(e,t){return this.getPoint(e,t)}getTangent(e,t=new de){return t.subVectors(this.v2,this.v1).normalize()}getTangentAt(e,t){return this.getTangent(e,t)}copy(e){return super.copy(e),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},Sa=class extends en{constructor(e=new N,t=new N){super(),this.isLineCurve3=!0,this.type="LineCurve3",this.v1=e,this.v2=t}getPoint(e,t=new N){let i=t;return e===1?i.copy(this.v2):(i.copy(this.v2).sub(this.v1),i.multiplyScalar(e).add(this.v1)),i}getPointAt(e,t){return this.getPoint(e,t)}getTangent(e,t=new N){return t.subVectors(this.v2,this.v1).normalize()}getTangentAt(e,t){return this.getTangent(e,t)}copy(e){return super.copy(e),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},cr=class extends en{constructor(e=new de,t=new de,i=new de){super(),this.isQuadraticBezierCurve=!0,this.type="QuadraticBezierCurve",this.v0=e,this.v1=t,this.v2=i}getPoint(e,t=new de){let i=t,s=this.v0,r=this.v1,a=this.v2;return i.set(Ws(e,s.x,r.x,a.x),Ws(e,s.y,r.y,a.y)),i}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},Ta=class extends en{constructor(e=new N,t=new N,i=new N){super(),this.isQuadraticBezierCurve3=!0,this.type="QuadraticBezierCurve3",this.v0=e,this.v1=t,this.v2=i}getPoint(e,t=new N){let i=t,s=this.v0,r=this.v1,a=this.v2;return i.set(Ws(e,s.x,r.x,a.x),Ws(e,s.y,r.y,a.y),Ws(e,s.z,r.z,a.z)),i}copy(e){return super.copy(e),this.v0.copy(e.v0),this.v1.copy(e.v1),this.v2.copy(e.v2),this}toJSON(){let e=super.toJSON();return e.v0=this.v0.toArray(),e.v1=this.v1.toArray(),e.v2=this.v2.toArray(),e}fromJSON(e){return super.fromJSON(e),this.v0.fromArray(e.v0),this.v1.fromArray(e.v1),this.v2.fromArray(e.v2),this}},hr=class extends en{constructor(e=[]){super(),this.isSplineCurve=!0,this.type="SplineCurve",this.points=e}getPoint(e,t=new de){let i=t,s=this.points,r=(s.length-1)*e,a=Math.floor(r),o=r-a,c=s[a===0?a:a-1],l=s[a],u=s[a>s.length-2?s.length-1:a+1],h=s[a>s.length-3?s.length-1:a+2];return i.set(Vh(o,c.x,l.x,u.x,h.x),Vh(o,c.y,l.y,u.y,h.y)),i}copy(e){super.copy(e),this.points=[];for(let t=0,i=e.points.length;t<i;t++){let s=e.points[t];this.points.push(s.clone())}return this}toJSON(){let e=super.toJSON();e.points=[];for(let t=0,i=this.points.length;t<i;t++){let s=this.points[t];e.points.push(s.toArray())}return e}fromJSON(e){super.fromJSON(e),this.points=[];for(let t=0,i=e.points.length;t<i;t++){let s=e.points[t];this.points.push(new de().fromArray(s))}return this}},Rl=Object.freeze({__proto__:null,ArcCurve:wa,CatmullRomCurve3:ba,CubicBezierCurve:or,CubicBezierCurve3:Ma,EllipseCurve:gs,LineCurve:lr,LineCurve3:Sa,QuadraticBezierCurve:cr,QuadraticBezierCurve3:Ta,SplineCurve:hr}),Ea=class extends en{constructor(){super(),this.type="CurvePath",this.curves=[],this.autoClose=!1}add(e){this.curves.push(e)}closePath(){let e=this.curves[0].getPoint(0),t=this.curves[this.curves.length-1].getPoint(1);if(!e.equals(t)){let i=e.isVector2===!0?"LineCurve":"LineCurve3";this.curves.push(new Rl[i](t,e))}return this}getPoint(e,t){let i=e*this.getLength(),s=this.getCurveLengths(),r=0;for(;r<s.length;){if(s[r]>=i){let a=s[r]-i,o=this.curves[r],c=o.getLength(),l=c===0?0:1-a/c;return o.getPointAt(l,t)}r++}return null}getLength(){let e=this.getCurveLengths();return e[e.length-1]}updateArcLengths(){this.needsUpdate=!0,this.cacheLengths=null,this.getCurveLengths()}getCurveLengths(){if(this.cacheLengths&&this.cacheLengths.length===this.curves.length)return this.cacheLengths;let e=[],t=0;for(let i=0,s=this.curves.length;i<s;i++)t+=this.curves[i].getLength(),e.push(t);return this.cacheLengths=e,e}getSpacedPoints(e=40){let t=[];for(let i=0;i<=e;i++)t.push(this.getPoint(i/e));return this.autoClose&&t.push(t[0]),t}getPoints(e=12){let t=[],i;for(let s=0,r=this.curves;s<r.length;s++){let a=r[s],o=a.isEllipseCurve?e*2:a.isLineCurve||a.isLineCurve3?1:a.isSplineCurve?e*a.points.length:e,c=a.getPoints(o);for(let l=0;l<c.length;l++){let u=c[l];i&&i.equals(u)||(t.push(u),i=u)}}return this.autoClose&&t.length>1&&!t[t.length-1].equals(t[0])&&t.push(t[0]),t}copy(e){super.copy(e),this.curves=[];for(let t=0,i=e.curves.length;t<i;t++){let s=e.curves[t];this.curves.push(s.clone())}return this.autoClose=e.autoClose,this}toJSON(){let e=super.toJSON();e.autoClose=this.autoClose,e.curves=[];for(let t=0,i=this.curves.length;t<i;t++){let s=this.curves[t];e.curves.push(s.toJSON())}return e}fromJSON(e){super.fromJSON(e),this.autoClose=e.autoClose,this.curves=[];for(let t=0,i=e.curves.length;t<i;t++){let s=e.curves[t];this.curves.push(new Rl[s.type]().fromJSON(s))}return this}},ur=class extends Ea{constructor(e){super(),this.type="Path",this.currentPoint=new de,e&&this.setFromPoints(e)}setFromPoints(e){this.moveTo(e[0].x,e[0].y);for(let t=1,i=e.length;t<i;t++)this.lineTo(e[t].x,e[t].y);return this}moveTo(e,t){return this.currentPoint.set(e,t),this}lineTo(e,t){let i=new lr(this.currentPoint.clone(),new de(e,t));return this.curves.push(i),this.currentPoint.set(e,t),this}quadraticCurveTo(e,t,i,s){let r=new cr(this.currentPoint.clone(),new de(e,t),new de(i,s));return this.curves.push(r),this.currentPoint.set(i,s),this}bezierCurveTo(e,t,i,s,r,a){let o=new or(this.currentPoint.clone(),new de(e,t),new de(i,s),new de(r,a));return this.curves.push(o),this.currentPoint.set(r,a),this}splineThru(e){let t=[this.currentPoint.clone()].concat(e),i=new hr(t);return this.curves.push(i),this.currentPoint.copy(e[e.length-1]),this}arc(e,t,i,s,r,a){let o=this.currentPoint.x,c=this.currentPoint.y;return this.absarc(e+o,t+c,i,s,r,a),this}absarc(e,t,i,s,r,a){return this.absellipse(e,t,i,i,s,r,a),this}ellipse(e,t,i,s,r,a,o,c){let l=this.currentPoint.x,u=this.currentPoint.y;return this.absellipse(e+l,t+u,i,s,r,a,o,c),this}absellipse(e,t,i,s,r,a,o,c){let l=new gs(e,t,i,s,r,a,o,c);if(this.curves.length>0){let h=l.getPoint(0);h.equals(this.currentPoint)||this.lineTo(h.x,h.y)}this.curves.push(l);let u=l.getPoint(1);return this.currentPoint.copy(u),this}copy(e){return super.copy(e),this.currentPoint.copy(e.currentPoint),this}toJSON(){let e=super.toJSON();return e.currentPoint=this.currentPoint.toArray(),e}fromJSON(e){return super.fromJSON(e),this.currentPoint.fromArray(e.currentPoint),this}},_s=class extends ur{constructor(e){super(e),this.uuid=Fi(),this.type="Shape",this.holes=[]}getPointsHoles(e){let t=[];for(let i=0,s=this.holes.length;i<s;i++)t[i]=this.holes[i].getPoints(e);return t}extractPoints(e){return{shape:this.getPoints(e),holes:this.getPointsHoles(e)}}copy(e){super.copy(e),this.holes=[];for(let t=0,i=e.holes.length;t<i;t++){let s=e.holes[t];this.holes.push(s.clone())}return this}toJSON(){let e=super.toJSON();e.uuid=this.uuid,e.holes=[];for(let t=0,i=this.holes.length;t<i;t++){let s=this.holes[t];e.holes.push(s.toJSON())}return e}fromJSON(e){super.fromJSON(e),this.uuid=e.uuid,this.holes=[];for(let t=0,i=e.holes.length;t<i;t++){let s=e.holes[t];this.holes.push(new ur().fromJSON(s))}return this}};function gp(n,e,t=2){let i=e&&e.length,s=i?e[0]*t:n.length,r=Ou(n,0,s,t,!0),a=[];if(!r||r.next===r.prev)return a;let o,c,l;if(i&&(r=wp(n,e,r,t)),n.length>80*t){o=1/0,c=1/0;let u=-1/0,h=-1/0;for(let d=t;d<s;d+=t){let f=n[d],g=n[d+1];f<o&&(o=f),g<c&&(c=g),f>u&&(u=f),g>h&&(h=g)}l=Math.max(u-o,h-c),l=l!==0?32767/l:0}return dr(r,a,t,o,c,l,0),a}function Ou(n,e,t,i,s){let r;if(s===Np(n,e,t,i)>0)for(let a=e;a<t;a+=i)r=Hh(a/i|0,n[a],n[a+1],r);else for(let a=t-i;a>=e;a-=i)r=Hh(a/i|0,n[a],n[a+1],r);return r&&xs(r,r.next)&&(pr(r),r=r.next),r}function Pi(n,e){if(!n)return n;e||(e=n);let t=n,i;do if(i=!1,!t.steiner&&(xs(t,t.next)||yt(t.prev,t,t.next)===0)){if(pr(t),t=e=t.prev,t===t.next)break;i=!0}else t=t.next;while(i||t!==e);return e}function dr(n,e,t,i,s,r,a){if(!n)return;!a&&r&&Ep(n,i,s,r);let o=n;for(;n.prev!==n.next;){let c=n.prev,l=n.next;if(r?xp(n,i,s,r):_p(n)){e.push(c.i,n.i,l.i),pr(n),n=l.next,o=l.next;continue}if(n=l,n===o){a?a===1?(n=vp(Pi(n),e),dr(n,e,t,i,s,r,2)):a===2&&yp(n,e,t,i,s,r):dr(Pi(n),e,t,i,s,r,1);break}}}function _p(n){let e=n.prev,t=n,i=n.next;if(yt(e,t,i)>=0)return!1;let s=e.x,r=t.x,a=i.x,o=e.y,c=t.y,l=i.y,u=Math.min(s,r,a),h=Math.min(o,c,l),d=Math.max(s,r,a),f=Math.max(o,c,l),g=i.next;for(;g!==e;){if(g.x>=u&&g.x<=d&&g.y>=h&&g.y<=f&&Vs(s,o,r,c,a,l,g.x,g.y)&&yt(g.prev,g,g.next)>=0)return!1;g=g.next}return!0}function xp(n,e,t,i){let s=n.prev,r=n,a=n.next;if(yt(s,r,a)>=0)return!1;let o=s.x,c=r.x,l=a.x,u=s.y,h=r.y,d=a.y,f=Math.min(o,c,l),g=Math.min(u,h,d),x=Math.max(o,c,l),m=Math.max(u,h,d),p=Pl(f,g,e,t,i),T=Pl(x,m,e,t,i),M=n.prevZ,y=n.nextZ;for(;M&&M.z>=p&&y&&y.z<=T;){if(M.x>=f&&M.x<=x&&M.y>=g&&M.y<=m&&M!==s&&M!==a&&Vs(o,u,c,h,l,d,M.x,M.y)&&yt(M.prev,M,M.next)>=0||(M=M.prevZ,y.x>=f&&y.x<=x&&y.y>=g&&y.y<=m&&y!==s&&y!==a&&Vs(o,u,c,h,l,d,y.x,y.y)&&yt(y.prev,y,y.next)>=0))return!1;y=y.nextZ}for(;M&&M.z>=p;){if(M.x>=f&&M.x<=x&&M.y>=g&&M.y<=m&&M!==s&&M!==a&&Vs(o,u,c,h,l,d,M.x,M.y)&&yt(M.prev,M,M.next)>=0)return!1;M=M.prevZ}for(;y&&y.z<=T;){if(y.x>=f&&y.x<=x&&y.y>=g&&y.y<=m&&y!==s&&y!==a&&Vs(o,u,c,h,l,d,y.x,y.y)&&yt(y.prev,y,y.next)>=0)return!1;y=y.nextZ}return!0}function vp(n,e){let t=n;do{let i=t.prev,s=t.next.next;!xs(i,s)&&Bu(i,t,t.next,s)&&fr(i,s)&&fr(s,i)&&(e.push(i.i,t.i,s.i),pr(t),pr(t.next),t=n=s),t=t.next}while(t!==n);return Pi(t)}function yp(n,e,t,i,s,r){let a=n;do{let o=a.next.next;for(;o!==a.prev;){if(a.i!==o.i&&Rp(a,o)){let c=zu(a,o);a=Pi(a,a.next),c=Pi(c,c.next),dr(a,e,t,i,s,r,0),dr(c,e,t,i,s,r,0);return}o=o.next}a=a.next}while(a!==n)}function wp(n,e,t,i){let s=[];for(let r=0,a=e.length;r<a;r++){let o=e[r]*i,c=r<a-1?e[r+1]*i:n.length,l=Ou(n,o,c,i,!1);l===l.next&&(l.steiner=!0),s.push(Cp(l))}s.sort(bp);for(let r=0;r<s.length;r++)t=Mp(s[r],t);return t}function bp(n,e){let t=n.x-e.x;if(t===0&&(t=n.y-e.y,t===0)){let i=(n.next.y-n.y)/(n.next.x-n.x),s=(e.next.y-e.y)/(e.next.x-e.x);t=i-s}return t}function Mp(n,e){let t=Sp(n,e);if(!t)return e;let i=zu(t,n);return Pi(i,i.next),Pi(t,t.next)}function Sp(n,e){let t=e,i=n.x,s=n.y,r=-1/0,a;if(xs(n,t))return t;do{if(xs(n,t.next))return t.next;if(s<=t.y&&s>=t.next.y&&t.next.y!==t.y){let h=t.x+(s-t.y)*(t.next.x-t.x)/(t.next.y-t.y);if(h<=i&&h>r&&(r=h,a=t.x<t.next.x?t:t.next,h===i))return a}t=t.next}while(t!==e);if(!a)return null;let o=a,c=a.x,l=a.y,u=1/0;t=a;do{if(i>=t.x&&t.x>=c&&i!==t.x&&ku(s<l?i:r,s,c,l,s<l?r:i,s,t.x,t.y)){let h=Math.abs(s-t.y)/(i-t.x);fr(t,n)&&(h<u||h===u&&(t.x>a.x||t.x===a.x&&Tp(a,t)))&&(a=t,u=h)}t=t.next}while(t!==o);return a}function Tp(n,e){return yt(n.prev,n,e.prev)<0&&yt(e.next,n,n.next)<0}function Ep(n,e,t,i){let s=n;do s.z===0&&(s.z=Pl(s.x,s.y,e,t,i)),s.prevZ=s.prev,s.nextZ=s.next,s=s.next;while(s!==n);s.prevZ.nextZ=null,s.prevZ=null,Ap(s)}function Ap(n){let e,t=1;do{let i=n,s;n=null;let r=null;for(e=0;i;){e++;let a=i,o=0;for(let l=0;l<t&&(o++,a=a.nextZ,!!a);l++);let c=t;for(;o>0||c>0&&a;)o!==0&&(c===0||!a||i.z<=a.z)?(s=i,i=i.nextZ,o--):(s=a,a=a.nextZ,c--),r?r.nextZ=s:n=s,s.prevZ=r,r=s;i=a}r.nextZ=null,t*=2}while(e>1);return n}function Pl(n,e,t,i,s){return n=(n-t)*s|0,e=(e-i)*s|0,n=(n|n<<8)&16711935,n=(n|n<<4)&252645135,n=(n|n<<2)&858993459,n=(n|n<<1)&1431655765,e=(e|e<<8)&16711935,e=(e|e<<4)&252645135,e=(e|e<<2)&858993459,e=(e|e<<1)&1431655765,n|e<<1}function Cp(n){let e=n,t=n;do(e.x<t.x||e.x===t.x&&e.y<t.y)&&(t=e),e=e.next;while(e!==n);return t}function ku(n,e,t,i,s,r,a,o){return(s-a)*(e-o)>=(n-a)*(r-o)&&(n-a)*(i-o)>=(t-a)*(e-o)&&(t-a)*(r-o)>=(s-a)*(i-o)}function Vs(n,e,t,i,s,r,a,o){return!(n===a&&e===o)&&ku(n,e,t,i,s,r,a,o)}function Rp(n,e){return n.next.i!==e.i&&n.prev.i!==e.i&&!Pp(n,e)&&(fr(n,e)&&fr(e,n)&&Ip(n,e)&&(yt(n.prev,n,e.prev)||yt(n,e.prev,e))||xs(n,e)&&yt(n.prev,n,n.next)>0&&yt(e.prev,e,e.next)>0)}function yt(n,e,t){return(e.y-n.y)*(t.x-e.x)-(e.x-n.x)*(t.y-e.y)}function xs(n,e){return n.x===e.x&&n.y===e.y}function Bu(n,e,t,i){let s=la(yt(n,e,t)),r=la(yt(n,e,i)),a=la(yt(t,i,n)),o=la(yt(t,i,e));return!!(s!==r&&a!==o||s===0&&oa(n,t,e)||r===0&&oa(n,i,e)||a===0&&oa(t,n,i)||o===0&&oa(t,e,i))}function oa(n,e,t){return e.x<=Math.max(n.x,t.x)&&e.x>=Math.min(n.x,t.x)&&e.y<=Math.max(n.y,t.y)&&e.y>=Math.min(n.y,t.y)}function la(n){return n>0?1:n<0?-1:0}function Pp(n,e){let t=n;do{if(t.i!==n.i&&t.next.i!==n.i&&t.i!==e.i&&t.next.i!==e.i&&Bu(t,t.next,n,e))return!0;t=t.next}while(t!==n);return!1}function fr(n,e){return yt(n.prev,n,n.next)<0?yt(n,e,n.next)>=0&&yt(n,n.prev,e)>=0:yt(n,e,n.prev)<0||yt(n,n.next,e)<0}function Ip(n,e){let t=n,i=!1,s=(n.x+e.x)/2,r=(n.y+e.y)/2;do t.y>r!=t.next.y>r&&t.next.y!==t.y&&s<(t.next.x-t.x)*(r-t.y)/(t.next.y-t.y)+t.x&&(i=!i),t=t.next;while(t!==n);return i}function zu(n,e){let t=Il(n.i,n.x,n.y),i=Il(e.i,e.x,e.y),s=n.next,r=e.prev;return n.next=e,e.prev=n,t.next=s,s.prev=t,i.next=t,t.prev=i,r.next=i,i.prev=r,i}function Hh(n,e,t,i){let s=Il(n,e,t);return i?(s.next=i.next,s.prev=i,i.next.prev=s,i.next=s):(s.prev=s,s.next=s),s}function pr(n){n.next.prev=n.prev,n.prev.next=n.next,n.prevZ&&(n.prevZ.nextZ=n.nextZ),n.nextZ&&(n.nextZ.prevZ=n.prevZ)}function Il(n,e,t){return{i:n,x:e,y:t,prev:null,next:null,z:0,prevZ:null,nextZ:null,steiner:!1}}function Np(n,e,t,i){let s=0;for(let r=e,a=t-i;r<t;r+=i)s+=(n[a]-n[r])*(n[r+1]+n[a+1]),a=r;return s}var Nl=class{static triangulate(e,t,i=2){return gp(e,t,i)}},Ei=class n{static area(e){let t=e.length,i=0;for(let s=t-1,r=0;r<t;s=r++)i+=e[s].x*e[r].y-e[r].x*e[s].y;return i*.5}static isClockWise(e){return n.area(e)<0}static triangulateShape(e,t){let i=[],s=[],r=[];Gh(e),Wh(i,e);let a=e.length;t.forEach(Gh);for(let c=0;c<t.length;c++)s.push(a),a+=t[c].length,Wh(i,t[c]);let o=Nl.triangulate(i,s);for(let c=0;c<o.length;c+=3)r.push(o.slice(c,c+3));return r}};function Gh(n){let e=n.length;e>2&&n[e-1].equals(n[0])&&n.pop()}function Wh(n,e){for(let t=0;t<e.length;t++)n.push(e[t].x),n.push(e[t].y)}var mr=class n extends cn{constructor(e=new _s([new de(.5,.5),new de(-.5,.5),new de(-.5,-.5),new de(.5,-.5)]),t={}){super(),this.type="ExtrudeGeometry",this.parameters={shapes:e,options:t},e=Array.isArray(e)?e:[e];let i=this,s=[],r=[];for(let o=0,c=e.length;o<c;o++){let l=e[o];a(l)}this.setAttribute("position",new Gt(s,3)),this.setAttribute("uv",new Gt(r,2)),this.computeVertexNormals();function a(o){let c=[],l=t.curveSegments!==void 0?t.curveSegments:12,u=t.steps!==void 0?t.steps:1,h=t.depth!==void 0?t.depth:1,d=t.bevelEnabled!==void 0?t.bevelEnabled:!0,f=t.bevelThickness!==void 0?t.bevelThickness:.2,g=t.bevelSize!==void 0?t.bevelSize:f-.1,x=t.bevelOffset!==void 0?t.bevelOffset:0,m=t.bevelSegments!==void 0?t.bevelSegments:3,p=t.extrudePath,T=t.UVGenerator!==void 0?t.UVGenerator:Dp,M,y=!1,R,E,P,D;p&&(M=p.getSpacedPoints(u),y=!0,d=!1,R=p.computeFrenetFrames(u,!1),E=new N,P=new N,D=new N),d||(m=0,f=0,g=0,x=0);let b=o.extractPoints(l),w=b.shape,C=b.holes;if(!Ei.isClockWise(w)){w=w.reverse();for(let ne=0,J=C.length;ne<J;ne++){let Z=C[ne];Ei.isClockWise(Z)&&(C[ne]=Z.reverse())}}function G(ne){let Z=10000000000000001e-36,$=ne[0];for(let pe=1;pe<=ne.length;pe++){let re=pe%ne.length,me=ne[re],We=me.x-$.x,He=me.y-$.y,S=We*We+He*He,_=Math.max(Math.abs(me.x),Math.abs(me.y),Math.abs($.x),Math.abs($.y)),O=Z*_*_;if(S<=O){ne.splice(re,1),pe--;continue}$=me}}G(w),C.forEach(G);let q=C.length,X=w;for(let ne=0;ne<q;ne++){let J=C[ne];w=w.concat(J)}function V(ne,J,Z){return J||console.error("THREE.ExtrudeGeometry: vec does not exist"),ne.clone().addScaledVector(J,Z)}let te=w.length;function U(ne,J,Z){let $,pe,re,me=ne.x-J.x,We=ne.y-J.y,He=Z.x-ne.x,S=Z.y-ne.y,_=me*me+We*We,O=me*S-We*He;if(Math.abs(O)>Number.EPSILON){let H=Math.sqrt(_),ee=Math.sqrt(He*He+S*S),W=J.x-We/H,Ne=J.y+me/H,fe=Z.x-S/ee,Ce=Z.y+He/ee,Re=((fe-W)*S-(Ce-Ne)*He)/(me*S-We*He);$=W+me*Re-ne.x,pe=Ne+We*Re-ne.y;let ae=$*$+pe*pe;if(ae<=2)return new de($,pe);re=Math.sqrt(ae/2)}else{let H=!1;me>Number.EPSILON?He>Number.EPSILON&&(H=!0):me<-Number.EPSILON?He<-Number.EPSILON&&(H=!0):Math.sign(We)===Math.sign(S)&&(H=!0),H?($=-We,pe=me,re=Math.sqrt(_)):($=me,pe=We,re=Math.sqrt(_/2))}return new de($/re,pe/re)}let Q=[];for(let ne=0,J=X.length,Z=J-1,$=ne+1;ne<J;ne++,Z++,$++)Z===J&&(Z=0),$===J&&($=0),Q[ne]=U(X[ne],X[Z],X[$]);let he=[],ue,ze=Q.concat();for(let ne=0,J=q;ne<J;ne++){let Z=C[ne];ue=[];for(let $=0,pe=Z.length,re=pe-1,me=$+1;$<pe;$++,re++,me++)re===pe&&(re=0),me===pe&&(me=0),ue[$]=U(Z[$],Z[re],Z[me]);he.push(ue),ze=ze.concat(ue)}let je;if(m===0)je=Ei.triangulateShape(X,C);else{let ne=[],J=[];for(let Z=0;Z<m;Z++){let $=Z/m,pe=f*Math.cos($*Math.PI/2),re=g*Math.sin($*Math.PI/2)+x;for(let me=0,We=X.length;me<We;me++){let He=V(X[me],Q[me],re);Ue(He.x,He.y,-pe),$===0&&ne.push(He)}for(let me=0,We=q;me<We;me++){let He=C[me];ue=he[me];let S=[];for(let _=0,O=He.length;_<O;_++){let H=V(He[_],ue[_],re);Ue(H.x,H.y,-pe),$===0&&S.push(H)}$===0&&J.push(S)}}je=Ei.triangulateShape(ne,J)}let Qe=je.length,it=g+x;for(let ne=0;ne<te;ne++){let J=d?V(w[ne],ze[ne],it):w[ne];y?(P.copy(R.normals[0]).multiplyScalar(J.x),E.copy(R.binormals[0]).multiplyScalar(J.y),D.copy(M[0]).add(P).add(E),Ue(D.x,D.y,D.z)):Ue(J.x,J.y,0)}for(let ne=1;ne<=u;ne++)for(let J=0;J<te;J++){let Z=d?V(w[J],ze[J],it):w[J];y?(P.copy(R.normals[ne]).multiplyScalar(Z.x),E.copy(R.binormals[ne]).multiplyScalar(Z.y),D.copy(M[ne]).add(P).add(E),Ue(D.x,D.y,D.z)):Ue(Z.x,Z.y,h/u*ne)}for(let ne=m-1;ne>=0;ne--){let J=ne/m,Z=f*Math.cos(J*Math.PI/2),$=g*Math.sin(J*Math.PI/2)+x;for(let pe=0,re=X.length;pe<re;pe++){let me=V(X[pe],Q[pe],$);Ue(me.x,me.y,h+Z)}for(let pe=0,re=C.length;pe<re;pe++){let me=C[pe];ue=he[pe];for(let We=0,He=me.length;We<He;We++){let S=V(me[We],ue[We],$);y?Ue(S.x,S.y+M[u-1].y,M[u-1].x+Z):Ue(S.x,S.y,h+Z)}}}Y(),se();function Y(){let ne=s.length/3;if(d){let J=0,Z=te*J;for(let $=0;$<Qe;$++){let pe=je[$];Ae(pe[2]+Z,pe[1]+Z,pe[0]+Z)}J=u+m*2,Z=te*J;for(let $=0;$<Qe;$++){let pe=je[$];Ae(pe[0]+Z,pe[1]+Z,pe[2]+Z)}}else{for(let J=0;J<Qe;J++){let Z=je[J];Ae(Z[2],Z[1],Z[0])}for(let J=0;J<Qe;J++){let Z=je[J];Ae(Z[0]+te*u,Z[1]+te*u,Z[2]+te*u)}}i.addGroup(ne,s.length/3-ne,0)}function se(){let ne=s.length/3,J=0;Me(X,J),J+=X.length;for(let Z=0,$=C.length;Z<$;Z++){let pe=C[Z];Me(pe,J),J+=pe.length}i.addGroup(ne,s.length/3-ne,1)}function Me(ne,J){let Z=ne.length;for(;--Z>=0;){let $=Z,pe=Z-1;pe<0&&(pe=ne.length-1);for(let re=0,me=u+m*2;re<me;re++){let We=te*re,He=te*(re+1),S=J+$+We,_=J+pe+We,O=J+pe+He,H=J+$+He;et(S,_,O,H)}}}function Ue(ne,J,Z){c.push(ne),c.push(J),c.push(Z)}function Ae(ne,J,Z){ft(ne),ft(J),ft(Z);let $=s.length/3,pe=T.generateTopUV(i,s,$-3,$-2,$-1);A(pe[0]),A(pe[1]),A(pe[2])}function et(ne,J,Z,$){ft(ne),ft(J),ft($),ft(J),ft(Z),ft($);let pe=s.length/3,re=T.generateSideWallUV(i,s,pe-6,pe-3,pe-2,pe-1);A(re[0]),A(re[1]),A(re[3]),A(re[1]),A(re[2]),A(re[3])}function ft(ne){s.push(c[ne*3+0]),s.push(c[ne*3+1]),s.push(c[ne*3+2])}function A(ne){r.push(ne.x),r.push(ne.y)}}}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}toJSON(){let e=super.toJSON(),t=this.parameters.shapes,i=this.parameters.options;return Lp(t,i,e)}static fromJSON(e,t){let i=[];for(let r=0,a=e.shapes.length;r<a;r++){let o=t[e.shapes[r]];i.push(o)}let s=e.options.extrudePath;return s!==void 0&&(e.options.extrudePath=new Rl[s.type]().fromJSON(s)),new n(i,e.options)}},Dp={generateTopUV:function(n,e,t,i,s){let r=e[t*3],a=e[t*3+1],o=e[i*3],c=e[i*3+1],l=e[s*3],u=e[s*3+1];return[new de(r,a),new de(o,c),new de(l,u)]},generateSideWallUV:function(n,e,t,i,s,r){let a=e[t*3],o=e[t*3+1],c=e[t*3+2],l=e[i*3],u=e[i*3+1],h=e[i*3+2],d=e[s*3],f=e[s*3+1],g=e[s*3+2],x=e[r*3],m=e[r*3+1],p=e[r*3+2];return Math.abs(o-u)<Math.abs(a-l)?[new de(a,1-c),new de(l,1-h),new de(d,1-g),new de(x,1-p)]:[new de(o,1-c),new de(u,1-h),new de(f,1-g),new de(m,1-p)]}};function Lp(n,e,t){if(t.shapes=[],Array.isArray(n))for(let i=0,s=n.length;i<s;i++){let r=n[i];t.shapes.push(r.uuid)}else t.shapes.push(n.uuid);return t.options=Object.assign({},e),e.extrudePath!==void 0&&(t.options.extrudePath=e.extrudePath.toJSON()),t}var gr=class n extends cn{constructor(e=1,t=1,i=1,s=1){super(),this.type="PlaneGeometry",this.parameters={width:e,height:t,widthSegments:i,heightSegments:s};let r=e/2,a=t/2,o=Math.floor(i),c=Math.floor(s),l=o+1,u=c+1,h=e/o,d=t/c,f=[],g=[],x=[],m=[];for(let p=0;p<u;p++){let T=p*d-a;for(let M=0;M<l;M++){let y=M*h-r;g.push(y,-T,0),x.push(0,0,1),m.push(M/o),m.push(1-p/c)}}for(let p=0;p<c;p++)for(let T=0;T<o;T++){let M=T+l*p,y=T+l*(p+1),R=T+1+l*(p+1),E=T+1+l*p;f.push(M,y,E),f.push(y,R,E)}this.setIndex(f),this.setAttribute("position",new Gt(g,3)),this.setAttribute("normal",new Gt(x,3)),this.setAttribute("uv",new Gt(m,2))}copy(e){return super.copy(e),this.parameters=Object.assign({},e.parameters),this}static fromJSON(e){return new n(e.width,e.height,e.widthSegments,e.heightSegments)}};var li=class extends ai{constructor(e){super(),this.isMeshStandardMaterial=!0,this.type="MeshStandardMaterial",this.defines={STANDARD:""},this.color=new qe(16777215),this.roughness=1,this.metalness=0,this.map=null,this.lightMap=null,this.lightMapIntensity=1,this.aoMap=null,this.aoMapIntensity=1,this.emissive=new qe(0),this.emissiveIntensity=1,this.emissiveMap=null,this.bumpMap=null,this.bumpScale=1,this.normalMap=null,this.normalMapType=Ql,this.normalScale=new de(1,1),this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.roughnessMap=null,this.metalnessMap=null,this.alphaMap=null,this.envMap=null,this.envMapRotation=new _n,this.envMapIntensity=1,this.wireframe=!1,this.wireframeLinewidth=1,this.wireframeLinecap="round",this.wireframeLinejoin="round",this.flatShading=!1,this.fog=!0,this.setValues(e)}copy(e){return super.copy(e),this.defines={STANDARD:""},this.color.copy(e.color),this.roughness=e.roughness,this.metalness=e.metalness,this.map=e.map,this.lightMap=e.lightMap,this.lightMapIntensity=e.lightMapIntensity,this.aoMap=e.aoMap,this.aoMapIntensity=e.aoMapIntensity,this.emissive.copy(e.emissive),this.emissiveMap=e.emissiveMap,this.emissiveIntensity=e.emissiveIntensity,this.bumpMap=e.bumpMap,this.bumpScale=e.bumpScale,this.normalMap=e.normalMap,this.normalMapType=e.normalMapType,this.normalScale.copy(e.normalScale),this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.roughnessMap=e.roughnessMap,this.metalnessMap=e.metalnessMap,this.alphaMap=e.alphaMap,this.envMap=e.envMap,this.envMapRotation.copy(e.envMapRotation),this.envMapIntensity=e.envMapIntensity,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this.wireframeLinecap=e.wireframeLinecap,this.wireframeLinejoin=e.wireframeLinejoin,this.flatShading=e.flatShading,this.fog=e.fog,this}};var Aa=class extends ai{constructor(e){super(),this.isMeshDepthMaterial=!0,this.type="MeshDepthMaterial",this.depthPacking=Mu,this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.wireframe=!1,this.wireframeLinewidth=1,this.setValues(e)}copy(e){return super.copy(e),this.depthPacking=e.depthPacking,this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this.wireframe=e.wireframe,this.wireframeLinewidth=e.wireframeLinewidth,this}},Ca=class extends ai{constructor(e){super(),this.isMeshDistanceMaterial=!0,this.type="MeshDistanceMaterial",this.map=null,this.alphaMap=null,this.displacementMap=null,this.displacementScale=1,this.displacementBias=0,this.setValues(e)}copy(e){return super.copy(e),this.map=e.map,this.alphaMap=e.alphaMap,this.displacementMap=e.displacementMap,this.displacementScale=e.displacementScale,this.displacementBias=e.displacementBias,this}};function ca(n,e){return!n||n.constructor===e?n:typeof e.BYTES_PER_ELEMENT=="number"?new e(n):Array.prototype.slice.call(n)}function Up(n){return ArrayBuffer.isView(n)&&!(n instanceof DataView)}var Ii=class{constructor(e,t,i,s){this.parameterPositions=e,this._cachedIndex=0,this.resultBuffer=s!==void 0?s:new t.constructor(i),this.sampleValues=t,this.valueSize=i,this.settings=null,this.DefaultSettings_={}}evaluate(e){let t=this.parameterPositions,i=this._cachedIndex,s=t[i],r=t[i-1];n:{e:{let a;t:{i:if(!(e<s)){for(let o=i+2;;){if(s===void 0){if(e<r)break i;return i=t.length,this._cachedIndex=i,this.copySampleValue_(i-1)}if(i===o)break;if(r=s,s=t[++i],e<s)break e}a=t.length;break t}if(!(e>=r)){let o=t[1];e<o&&(i=2,r=o);for(let c=i-2;;){if(r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(i===c)break;if(s=r,r=t[--i-1],e>=r)break e}a=i,i=0;break t}break n}for(;i<a;){let o=i+a>>>1;e<t[o]?a=o:i=o+1}if(s=t[i],r=t[i-1],r===void 0)return this._cachedIndex=0,this.copySampleValue_(0);if(s===void 0)return i=t.length,this._cachedIndex=i,this.copySampleValue_(i-1)}this._cachedIndex=i,this.intervalChanged_(i,r,s)}return this.interpolate_(i,r,e,s)}getSettings_(){return this.settings||this.DefaultSettings_}copySampleValue_(e){let t=this.resultBuffer,i=this.sampleValues,s=this.valueSize,r=e*s;for(let a=0;a!==s;++a)t[a]=i[r+a];return t}interpolate_(){throw new Error("call to abstract method")}intervalChanged_(){}},Ra=class extends Ii{constructor(e,t,i,s){super(e,t,i,s),this._weightPrev=-0,this._offsetPrev=-0,this._weightNext=-0,this._offsetNext=-0,this.DefaultSettings_={endingStart:Sl,endingEnd:Sl}}intervalChanged_(e,t,i){let s=this.parameterPositions,r=e-2,a=e+1,o=s[r],c=s[a];if(o===void 0)switch(this.getSettings_().endingStart){case Tl:r=e,o=2*t-i;break;case El:r=s.length-2,o=t+s[r]-s[r+1];break;default:r=e,o=i}if(c===void 0)switch(this.getSettings_().endingEnd){case Tl:a=e,c=2*i-t;break;case El:a=1,c=i+s[1]-s[0];break;default:a=e-1,c=t}let l=(i-t)*.5,u=this.valueSize;this._weightPrev=l/(t-o),this._weightNext=l/(c-i),this._offsetPrev=r*u,this._offsetNext=a*u}interpolate_(e,t,i,s){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=e*o,l=c-o,u=this._offsetPrev,h=this._offsetNext,d=this._weightPrev,f=this._weightNext,g=(i-t)/(s-t),x=g*g,m=x*g,p=-d*m+2*d*x-d*g,T=(1+d)*m+(-1.5-2*d)*x+(-.5+d)*g+1,M=(-1-f)*m+(1.5+f)*x+.5*g,y=f*m-f*x;for(let R=0;R!==o;++R)r[R]=p*a[u+R]+T*a[l+R]+M*a[c+R]+y*a[h+R];return r}},Pa=class extends Ii{constructor(e,t,i,s){super(e,t,i,s)}interpolate_(e,t,i,s){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=e*o,l=c-o,u=(i-t)/(s-t),h=1-u;for(let d=0;d!==o;++d)r[d]=a[l+d]*h+a[c+d]*u;return r}},Ia=class extends Ii{constructor(e,t,i,s){super(e,t,i,s)}interpolate_(e){return this.copySampleValue_(e-1)}},tn=class{constructor(e,t,i,s){if(e===void 0)throw new Error("THREE.KeyframeTrack: track name is undefined");if(t===void 0||t.length===0)throw new Error("THREE.KeyframeTrack: no keyframes in track named "+e);this.name=e,this.times=ca(t,this.TimeBufferType),this.values=ca(i,this.ValueBufferType),this.setInterpolation(s||this.DefaultInterpolation)}static toJSON(e){let t=e.constructor,i;if(t.toJSON!==this.toJSON)i=t.toJSON(e);else{i={name:e.name,times:ca(e.times,Array),values:ca(e.values,Array)};let s=e.getInterpolation();s!==e.DefaultInterpolation&&(i.interpolation=s)}return i.type=e.ValueTypeName,i}InterpolantFactoryMethodDiscrete(e){return new Ia(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodLinear(e){return new Pa(this.times,this.values,this.getValueSize(),e)}InterpolantFactoryMethodSmooth(e){return new Ra(this.times,this.values,this.getValueSize(),e)}setInterpolation(e){let t;switch(e){case qs:t=this.InterpolantFactoryMethodDiscrete;break;case ma:t=this.InterpolantFactoryMethodLinear;break;case ha:t=this.InterpolantFactoryMethodSmooth;break}if(t===void 0){let i="unsupported interpolation for "+this.ValueTypeName+" keyframe track named "+this.name;if(this.createInterpolant===void 0)if(e!==this.DefaultInterpolation)this.setInterpolation(this.DefaultInterpolation);else throw new Error(i);return console.warn("THREE.KeyframeTrack:",i),this}return this.createInterpolant=t,this}getInterpolation(){switch(this.createInterpolant){case this.InterpolantFactoryMethodDiscrete:return qs;case this.InterpolantFactoryMethodLinear:return ma;case this.InterpolantFactoryMethodSmooth:return ha}}getValueSize(){return this.values.length/this.times.length}shift(e){if(e!==0){let t=this.times;for(let i=0,s=t.length;i!==s;++i)t[i]+=e}return this}scale(e){if(e!==1){let t=this.times;for(let i=0,s=t.length;i!==s;++i)t[i]*=e}return this}trim(e,t){let i=this.times,s=i.length,r=0,a=s-1;for(;r!==s&&i[r]<e;)++r;for(;a!==-1&&i[a]>t;)--a;if(++a,r!==0||a!==s){r>=a&&(a=Math.max(a,1),r=a-1);let o=this.getValueSize();this.times=i.slice(r,a),this.values=this.values.slice(r*o,a*o)}return this}validate(){let e=!0,t=this.getValueSize();t-Math.floor(t)!==0&&(console.error("THREE.KeyframeTrack: Invalid value size in track.",this),e=!1);let i=this.times,s=this.values,r=i.length;r===0&&(console.error("THREE.KeyframeTrack: Track is empty.",this),e=!1);let a=null;for(let o=0;o!==r;o++){let c=i[o];if(typeof c=="number"&&isNaN(c)){console.error("THREE.KeyframeTrack: Time is not a valid number.",this,o,c),e=!1;break}if(a!==null&&a>c){console.error("THREE.KeyframeTrack: Out of order keys.",this,o,c,a),e=!1;break}a=c}if(s!==void 0&&Up(s))for(let o=0,c=s.length;o!==c;++o){let l=s[o];if(isNaN(l)){console.error("THREE.KeyframeTrack: Value is not a valid number.",this,o,l),e=!1;break}}return e}optimize(){let e=this.times.slice(),t=this.values.slice(),i=this.getValueSize(),s=this.getInterpolation()===ha,r=e.length-1,a=1;for(let o=1;o<r;++o){let c=!1,l=e[o],u=e[o+1];if(l!==u&&(o!==1||l!==e[0]))if(s)c=!0;else{let h=o*i,d=h-i,f=h+i;for(let g=0;g!==i;++g){let x=t[h+g];if(x!==t[d+g]||x!==t[f+g]){c=!0;break}}}if(c){if(o!==a){e[a]=e[o];let h=o*i,d=a*i;for(let f=0;f!==i;++f)t[d+f]=t[h+f]}++a}}if(r>0){e[a]=e[r];for(let o=r*i,c=a*i,l=0;l!==i;++l)t[c+l]=t[o+l];++a}return a!==e.length?(this.times=e.slice(0,a),this.values=t.slice(0,a*i)):(this.times=e,this.values=t),this}clone(){let e=this.times.slice(),t=this.values.slice(),i=this.constructor,s=new i(this.name,e,t);return s.createInterpolant=this.createInterpolant,s}};tn.prototype.ValueTypeName="";tn.prototype.TimeBufferType=Float32Array;tn.prototype.ValueBufferType=Float32Array;tn.prototype.DefaultInterpolation=ma;var ci=class extends tn{constructor(e,t,i){super(e,t,i)}};ci.prototype.ValueTypeName="bool";ci.prototype.ValueBufferType=Array;ci.prototype.DefaultInterpolation=qs;ci.prototype.InterpolantFactoryMethodLinear=void 0;ci.prototype.InterpolantFactoryMethodSmooth=void 0;var Na=class extends tn{constructor(e,t,i,s){super(e,t,i,s)}};Na.prototype.ValueTypeName="color";var Da=class extends tn{constructor(e,t,i,s){super(e,t,i,s)}};Da.prototype.ValueTypeName="number";var La=class extends Ii{constructor(e,t,i,s){super(e,t,i,s)}interpolate_(e,t,i,s){let r=this.resultBuffer,a=this.sampleValues,o=this.valueSize,c=(i-t)/(s-t),l=e*o;for(let u=l+o;l!==u;l+=4)ln.slerpFlat(r,0,a,l-o,a,l,c);return r}},_r=class extends tn{constructor(e,t,i,s){super(e,t,i,s)}InterpolantFactoryMethodLinear(e){return new La(this.times,this.values,this.getValueSize(),e)}};_r.prototype.ValueTypeName="quaternion";_r.prototype.InterpolantFactoryMethodSmooth=void 0;var hi=class extends tn{constructor(e,t,i){super(e,t,i)}};hi.prototype.ValueTypeName="string";hi.prototype.ValueBufferType=Array;hi.prototype.DefaultInterpolation=qs;hi.prototype.InterpolantFactoryMethodLinear=void 0;hi.prototype.InterpolantFactoryMethodSmooth=void 0;var Ua=class extends tn{constructor(e,t,i,s){super(e,t,i,s)}};Ua.prototype.ValueTypeName="vector";var Dl={enabled:!1,files:{},add:function(n,e){this.enabled!==!1&&(this.files[n]=e)},get:function(n){if(this.enabled!==!1)return this.files[n]},remove:function(n){delete this.files[n]},clear:function(){this.files={}}},Fa=class{constructor(e,t,i){let s=this,r=!1,a=0,o=0,c,l=[];this.onStart=void 0,this.onLoad=e,this.onProgress=t,this.onError=i,this.abortController=new AbortController,this.itemStart=function(u){o++,r===!1&&s.onStart!==void 0&&s.onStart(u,a,o),r=!0},this.itemEnd=function(u){a++,s.onProgress!==void 0&&s.onProgress(u,a,o),a===o&&(r=!1,s.onLoad!==void 0&&s.onLoad())},this.itemError=function(u){s.onError!==void 0&&s.onError(u)},this.resolveURL=function(u){return c?c(u):u},this.setURLModifier=function(u){return c=u,this},this.addHandler=function(u,h){return l.push(u,h),this},this.removeHandler=function(u){let h=l.indexOf(u);return h!==-1&&l.splice(h,2),this},this.getHandler=function(u){for(let h=0,d=l.length;h<d;h+=2){let f=l[h],g=l[h+1];if(f.global&&(f.lastIndex=0),f.test(u))return g}return null},this.abort=function(){return this.abortController.abort(),this.abortController=new AbortController,this}}},Vu=new Fa,Ni=class{constructor(e){this.manager=e!==void 0?e:Vu,this.crossOrigin="anonymous",this.withCredentials=!1,this.path="",this.resourcePath="",this.requestHeader={}}load(){}loadAsync(e,t){let i=this;return new Promise(function(s,r){i.load(e,s,t,r)})}parse(){}setCrossOrigin(e){return this.crossOrigin=e,this}setWithCredentials(e){return this.withCredentials=e,this}setPath(e){return this.path=e,this}setResourcePath(e){return this.resourcePath=e,this}setRequestHeader(e){return this.requestHeader=e,this}abort(){return this}};Ni.DEFAULT_MATERIAL_NAME="__DEFAULT";var Hn={},Ll=class extends Error{constructor(e,t){super(e),this.response=t}},xr=class extends Ni{constructor(e){super(e),this.mimeType="",this.responseType="",this._abortController=new AbortController}load(e,t,i,s){e===void 0&&(e=""),this.path!==void 0&&(e=this.path+e),e=this.manager.resolveURL(e);let r=Dl.get(`file:${e}`);if(r!==void 0)return this.manager.itemStart(e),setTimeout(()=>{t&&t(r),this.manager.itemEnd(e)},0),r;if(Hn[e]!==void 0){Hn[e].push({onLoad:t,onProgress:i,onError:s});return}Hn[e]=[],Hn[e].push({onLoad:t,onProgress:i,onError:s});let a=new Request(e,{headers:new Headers(this.requestHeader),credentials:this.withCredentials?"include":"same-origin",signal:typeof AbortSignal.any=="function"?AbortSignal.any([this._abortController.signal,this.manager.abortController.signal]):this._abortController.signal}),o=this.mimeType,c=this.responseType;fetch(a).then(l=>{if(l.status===200||l.status===0){if(l.status===0&&console.warn("THREE.FileLoader: HTTP Status 0 received."),typeof ReadableStream>"u"||l.body===void 0||l.body.getReader===void 0)return l;let u=Hn[e],h=l.body.getReader(),d=l.headers.get("X-File-Size")||l.headers.get("Content-Length"),f=d?parseInt(d):0,g=f!==0,x=0,m=new ReadableStream({start(p){T();function T(){h.read().then(({done:M,value:y})=>{if(M)p.close();else{x+=y.byteLength;let R=new ProgressEvent("progress",{lengthComputable:g,loaded:x,total:f});for(let E=0,P=u.length;E<P;E++){let D=u[E];D.onProgress&&D.onProgress(R)}p.enqueue(y),T()}},M=>{p.error(M)})}}});return new Response(m)}else throw new Ll(`fetch for "${l.url}" responded with ${l.status}: ${l.statusText}`,l)}).then(l=>{switch(c){case"arraybuffer":return l.arrayBuffer();case"blob":return l.blob();case"document":return l.text().then(u=>new DOMParser().parseFromString(u,o));case"json":return l.json();default:if(o==="")return l.text();{let h=/charset="?([^;"\s]*)"?/i.exec(o),d=h&&h[1]?h[1].toLowerCase():void 0,f=new TextDecoder(d);return l.arrayBuffer().then(g=>f.decode(g))}}}).then(l=>{Dl.add(`file:${e}`,l);let u=Hn[e];delete Hn[e];for(let h=0,d=u.length;h<d;h++){let f=u[h];f.onLoad&&f.onLoad(l)}}).catch(l=>{let u=Hn[e];if(u===void 0)throw this.manager.itemError(e),l;delete Hn[e];for(let h=0,d=u.length;h<d;h++){let f=u[h];f.onError&&f.onError(l)}this.manager.itemError(e)}).finally(()=>{this.manager.itemEnd(e)}),this.manager.itemStart(e)}setResponseType(e){return this.responseType=e,this}setMimeType(e){return this.mimeType=e,this}abort(){return this._abortController.abort(),this._abortController=new AbortController,this}};var vr=class extends Ft{constructor(e,t=1){super(),this.isLight=!0,this.type="Light",this.color=new qe(e),this.intensity=t}dispose(){}copy(e,t){return super.copy(e,t),this.color.copy(e.color),this.intensity=e.intensity,this}toJSON(e){let t=super.toJSON(e);return t.object.color=this.color.getHex(),t.object.intensity=this.intensity,this.groundColor!==void 0&&(t.object.groundColor=this.groundColor.getHex()),this.distance!==void 0&&(t.object.distance=this.distance),this.angle!==void 0&&(t.object.angle=this.angle),this.decay!==void 0&&(t.object.decay=this.decay),this.penumbra!==void 0&&(t.object.penumbra=this.penumbra),this.shadow!==void 0&&(t.object.shadow=this.shadow.toJSON()),this.target!==void 0&&(t.object.target=this.target.uuid),t}},yr=class extends vr{constructor(e,t,i){super(e,i),this.isHemisphereLight=!0,this.type="HemisphereLight",this.position.copy(Ft.DEFAULT_UP),this.updateMatrix(),this.groundColor=new qe(t)}copy(e,t){return super.copy(e,t),this.groundColor.copy(e.groundColor),this}},Ml=new Mt,Xh=new N,qh=new N,Ul=class{constructor(e){this.camera=e,this.intensity=1,this.bias=0,this.normalBias=0,this.radius=1,this.blurSamples=8,this.mapSize=new de(512,512),this.mapType=vn,this.map=null,this.mapPass=null,this.matrix=new Mt,this.autoUpdate=!0,this.needsUpdate=!1,this._frustum=new ms,this._frameExtents=new de(1,1),this._viewportCount=1,this._viewports=[new wt(0,0,1,1)]}getViewportCount(){return this._viewportCount}getFrustum(){return this._frustum}updateMatrices(e){let t=this.camera,i=this.matrix;Xh.setFromMatrixPosition(e.matrixWorld),t.position.copy(Xh),qh.setFromMatrixPosition(e.target.matrixWorld),t.lookAt(qh),t.updateMatrixWorld(),Ml.multiplyMatrices(t.projectionMatrix,t.matrixWorldInverse),this._frustum.setFromProjectionMatrix(Ml,t.coordinateSystem,t.reversedDepth),t.reversedDepth?i.set(.5,0,0,.5,0,.5,0,.5,0,0,1,0,0,0,0,1):i.set(.5,0,0,.5,0,.5,0,.5,0,0,.5,.5,0,0,0,1),i.multiply(Ml)}getViewport(e){return this._viewports[e]}getFrameExtents(){return this._frameExtents}dispose(){this.map&&this.map.dispose(),this.mapPass&&this.mapPass.dispose()}copy(e){return this.camera=e.camera.clone(),this.intensity=e.intensity,this.bias=e.bias,this.radius=e.radius,this.autoUpdate=e.autoUpdate,this.needsUpdate=e.needsUpdate,this.normalBias=e.normalBias,this.blurSamples=e.blurSamples,this.mapSize.copy(e.mapSize),this}clone(){return new this.constructor().copy(this)}toJSON(){let e={};return this.intensity!==1&&(e.intensity=this.intensity),this.bias!==0&&(e.bias=this.bias),this.normalBias!==0&&(e.normalBias=this.normalBias),this.radius!==1&&(e.radius=this.radius),(this.mapSize.x!==512||this.mapSize.y!==512)&&(e.mapSize=this.mapSize.toArray()),e.camera=this.camera.toJSON(!1).object,delete e.camera.matrix,e}};var wr=class extends tr{constructor(e=-1,t=1,i=1,s=-1,r=.1,a=2e3){super(),this.isOrthographicCamera=!0,this.type="OrthographicCamera",this.zoom=1,this.view=null,this.left=e,this.right=t,this.top=i,this.bottom=s,this.near=r,this.far=a,this.updateProjectionMatrix()}copy(e,t){return super.copy(e,t),this.left=e.left,this.right=e.right,this.top=e.top,this.bottom=e.bottom,this.near=e.near,this.far=e.far,this.zoom=e.zoom,this.view=e.view===null?null:Object.assign({},e.view),this}setViewOffset(e,t,i,s,r,a){this.view===null&&(this.view={enabled:!0,fullWidth:1,fullHeight:1,offsetX:0,offsetY:0,width:1,height:1}),this.view.enabled=!0,this.view.fullWidth=e,this.view.fullHeight=t,this.view.offsetX=i,this.view.offsetY=s,this.view.width=r,this.view.height=a,this.updateProjectionMatrix()}clearViewOffset(){this.view!==null&&(this.view.enabled=!1),this.updateProjectionMatrix()}updateProjectionMatrix(){let e=(this.right-this.left)/(2*this.zoom),t=(this.top-this.bottom)/(2*this.zoom),i=(this.right+this.left)/2,s=(this.top+this.bottom)/2,r=i-e,a=i+e,o=s+t,c=s-t;if(this.view!==null&&this.view.enabled){let l=(this.right-this.left)/this.view.fullWidth/this.zoom,u=(this.top-this.bottom)/this.view.fullHeight/this.zoom;r+=l*this.view.offsetX,a=r+l*this.view.width,o-=u*this.view.offsetY,c=o-u*this.view.height}this.projectionMatrix.makeOrthographic(r,a,o,c,this.near,this.far,this.coordinateSystem,this.reversedDepth),this.projectionMatrixInverse.copy(this.projectionMatrix).invert()}toJSON(e){let t=super.toJSON(e);return t.object.zoom=this.zoom,t.object.left=this.left,t.object.right=this.right,t.object.top=this.top,t.object.bottom=this.bottom,t.object.near=this.near,t.object.far=this.far,this.view!==null&&(t.object.view=Object.assign({},this.view)),t}},Fl=class extends Ul{constructor(){super(new wr(-5,5,5,-5,.5,500)),this.isDirectionalLightShadow=!0}},Di=class extends vr{constructor(e,t){super(e,t),this.isDirectionalLight=!0,this.type="DirectionalLight",this.position.copy(Ft.DEFAULT_UP),this.updateMatrix(),this.target=new Ft,this.shadow=new Fl}dispose(){this.shadow.dispose()}copy(e){return super.copy(e),this.target=e.target.clone(),this.shadow=e.shadow.clone(),this}};var Oa=class extends Ut{constructor(e=[]){super(),this.isArrayCamera=!0,this.isMultiViewCamera=!1,this.cameras=e}};var oc="\\[\\]\\.:\\/",Fp=new RegExp("["+oc+"]","g"),lc="[^"+oc+"]",Op="[^"+oc.replace("\\.","")+"]",kp=/((?:WC+[\/:])*)/.source.replace("WC",lc),Bp=/(WCOD+)?/.source.replace("WCOD",Op),zp=/(?:\.(WC+)(?:\[(.+)\])?)?/.source.replace("WC",lc),Vp=/\.(WC+)(?:\[(.+)\])?/.source.replace("WC",lc),Hp=new RegExp("^"+kp+Bp+zp+Vp+"$"),Gp=["material","materials","bones","map"],Ol=class{constructor(e,t,i){let s=i||_t.parseTrackName(t);this._targetGroup=e,this._bindings=e.subscribe_(t,s)}getValue(e,t){this.bind();let i=this._targetGroup.nCachedObjects_,s=this._bindings[i];s!==void 0&&s.getValue(e,t)}setValue(e,t){let i=this._bindings;for(let s=this._targetGroup.nCachedObjects_,r=i.length;s!==r;++s)i[s].setValue(e,t)}bind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,i=e.length;t!==i;++t)e[t].bind()}unbind(){let e=this._bindings;for(let t=this._targetGroup.nCachedObjects_,i=e.length;t!==i;++t)e[t].unbind()}},_t=class n{constructor(e,t,i){this.path=t,this.parsedPath=i||n.parseTrackName(t),this.node=n.findNode(e,this.parsedPath.nodeName),this.rootNode=e,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}static create(e,t,i){return e&&e.isAnimationObjectGroup?new n.Composite(e,t,i):new n(e,t,i)}static sanitizeNodeName(e){return e.replace(/\s/g,"_").replace(Fp,"")}static parseTrackName(e){let t=Hp.exec(e);if(t===null)throw new Error("PropertyBinding: Cannot parse trackName: "+e);let i={nodeName:t[2],objectName:t[3],objectIndex:t[4],propertyName:t[5],propertyIndex:t[6]},s=i.nodeName&&i.nodeName.lastIndexOf(".");if(s!==void 0&&s!==-1){let r=i.nodeName.substring(s+1);Gp.indexOf(r)!==-1&&(i.nodeName=i.nodeName.substring(0,s),i.objectName=r)}if(i.propertyName===null||i.propertyName.length===0)throw new Error("PropertyBinding: can not parse propertyName from trackName: "+e);return i}static findNode(e,t){if(t===void 0||t===""||t==="."||t===-1||t===e.name||t===e.uuid)return e;if(e.skeleton){let i=e.skeleton.getBoneByName(t);if(i!==void 0)return i}if(e.children){let i=function(r){for(let a=0;a<r.length;a++){let o=r[a];if(o.name===t||o.uuid===t)return o;let c=i(o.children);if(c)return c}return null},s=i(e.children);if(s)return s}return null}_getValue_unavailable(){}_setValue_unavailable(){}_getValue_direct(e,t){e[t]=this.targetObject[this.propertyName]}_getValue_array(e,t){let i=this.resolvedProperty;for(let s=0,r=i.length;s!==r;++s)e[t++]=i[s]}_getValue_arrayElement(e,t){e[t]=this.resolvedProperty[this.propertyIndex]}_getValue_toArray(e,t){this.resolvedProperty.toArray(e,t)}_setValue_direct(e,t){this.targetObject[this.propertyName]=e[t]}_setValue_direct_setNeedsUpdate(e,t){this.targetObject[this.propertyName]=e[t],this.targetObject.needsUpdate=!0}_setValue_direct_setMatrixWorldNeedsUpdate(e,t){this.targetObject[this.propertyName]=e[t],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_array(e,t){let i=this.resolvedProperty;for(let s=0,r=i.length;s!==r;++s)i[s]=e[t++]}_setValue_array_setNeedsUpdate(e,t){let i=this.resolvedProperty;for(let s=0,r=i.length;s!==r;++s)i[s]=e[t++];this.targetObject.needsUpdate=!0}_setValue_array_setMatrixWorldNeedsUpdate(e,t){let i=this.resolvedProperty;for(let s=0,r=i.length;s!==r;++s)i[s]=e[t++];this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_arrayElement(e,t){this.resolvedProperty[this.propertyIndex]=e[t]}_setValue_arrayElement_setNeedsUpdate(e,t){this.resolvedProperty[this.propertyIndex]=e[t],this.targetObject.needsUpdate=!0}_setValue_arrayElement_setMatrixWorldNeedsUpdate(e,t){this.resolvedProperty[this.propertyIndex]=e[t],this.targetObject.matrixWorldNeedsUpdate=!0}_setValue_fromArray(e,t){this.resolvedProperty.fromArray(e,t)}_setValue_fromArray_setNeedsUpdate(e,t){this.resolvedProperty.fromArray(e,t),this.targetObject.needsUpdate=!0}_setValue_fromArray_setMatrixWorldNeedsUpdate(e,t){this.resolvedProperty.fromArray(e,t),this.targetObject.matrixWorldNeedsUpdate=!0}_getValue_unbound(e,t){this.bind(),this.getValue(e,t)}_setValue_unbound(e,t){this.bind(),this.setValue(e,t)}bind(){let e=this.node,t=this.parsedPath,i=t.objectName,s=t.propertyName,r=t.propertyIndex;if(e||(e=n.findNode(this.rootNode,t.nodeName),this.node=e),this.getValue=this._getValue_unavailable,this.setValue=this._setValue_unavailable,!e){console.warn("THREE.PropertyBinding: No target node found for track: "+this.path+".");return}if(i){let l=t.objectIndex;switch(i){case"materials":if(!e.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!e.material.materials){console.error("THREE.PropertyBinding: Can not bind to material.materials as node.material does not have a materials array.",this);return}e=e.material.materials;break;case"bones":if(!e.skeleton){console.error("THREE.PropertyBinding: Can not bind to bones as node does not have a skeleton.",this);return}e=e.skeleton.bones;for(let u=0;u<e.length;u++)if(e[u].name===l){l=u;break}break;case"map":if("map"in e){e=e.map;break}if(!e.material){console.error("THREE.PropertyBinding: Can not bind to material as node does not have a material.",this);return}if(!e.material.map){console.error("THREE.PropertyBinding: Can not bind to material.map as node.material does not have a map.",this);return}e=e.material.map;break;default:if(e[i]===void 0){console.error("THREE.PropertyBinding: Can not bind to objectName of node undefined.",this);return}e=e[i]}if(l!==void 0){if(e[l]===void 0){console.error("THREE.PropertyBinding: Trying to bind to objectIndex of objectName, but is undefined.",this,e);return}e=e[l]}}let a=e[s];if(a===void 0){let l=t.nodeName;console.error("THREE.PropertyBinding: Trying to update property for track: "+l+"."+s+" but it wasn't found.",e);return}let o=this.Versioning.None;this.targetObject=e,e.isMaterial===!0?o=this.Versioning.NeedsUpdate:e.isObject3D===!0&&(o=this.Versioning.MatrixWorldNeedsUpdate);let c=this.BindingType.Direct;if(r!==void 0){if(s==="morphTargetInfluences"){if(!e.geometry){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.",this);return}if(!e.geometry.morphAttributes){console.error("THREE.PropertyBinding: Can not bind to morphTargetInfluences because node does not have a geometry.morphAttributes.",this);return}e.morphTargetDictionary[r]!==void 0&&(r=e.morphTargetDictionary[r])}c=this.BindingType.ArrayElement,this.resolvedProperty=a,this.propertyIndex=r}else a.fromArray!==void 0&&a.toArray!==void 0?(c=this.BindingType.HasFromToArray,this.resolvedProperty=a):Array.isArray(a)?(c=this.BindingType.EntireArray,this.resolvedProperty=a):this.propertyName=s;this.getValue=this.GetterByBindingType[c],this.setValue=this.SetterByBindingTypeAndVersioning[c][o]}unbind(){this.node=null,this.getValue=this._getValue_unbound,this.setValue=this._setValue_unbound}};_t.Composite=Ol;_t.prototype.BindingType={Direct:0,EntireArray:1,ArrayElement:2,HasFromToArray:3};_t.prototype.Versioning={None:0,NeedsUpdate:1,MatrixWorldNeedsUpdate:2};_t.prototype.GetterByBindingType=[_t.prototype._getValue_direct,_t.prototype._getValue_array,_t.prototype._getValue_arrayElement,_t.prototype._getValue_toArray];_t.prototype.SetterByBindingTypeAndVersioning=[[_t.prototype._setValue_direct,_t.prototype._setValue_direct_setNeedsUpdate,_t.prototype._setValue_direct_setMatrixWorldNeedsUpdate],[_t.prototype._setValue_array,_t.prototype._setValue_array_setNeedsUpdate,_t.prototype._setValue_array_setMatrixWorldNeedsUpdate],[_t.prototype._setValue_arrayElement,_t.prototype._setValue_arrayElement_setNeedsUpdate,_t.prototype._setValue_arrayElement_setMatrixWorldNeedsUpdate],[_t.prototype._setValue_fromArray,_t.prototype._setValue_fromArray_setNeedsUpdate,_t.prototype._setValue_fromArray_setMatrixWorldNeedsUpdate]];var Bv=new Float32Array(1);var ui=class{constructor(e=1,t=0,i=0){this.radius=e,this.phi=t,this.theta=i}set(e,t,i){return this.radius=e,this.phi=t,this.theta=i,this}copy(e){return this.radius=e.radius,this.phi=e.phi,this.theta=e.theta,this}makeSafe(){return this.phi=Je(this.phi,1e-6,Math.PI-1e-6),this}setFromVector3(e){return this.setFromCartesianCoords(e.x,e.y,e.z)}setFromCartesianCoords(e,t,i){return this.radius=Math.sqrt(e*e+t*t+i*i),this.radius===0?(this.theta=0,this.phi=0):(this.theta=Math.atan2(e,i),this.phi=Math.acos(Je(t/this.radius,-1,1))),this}clone(){return new this.constructor().copy(this)}};var br=class extends Mn{constructor(e,t=null){super(),this.object=e,this.domElement=t,this.enabled=!0,this.state=-1,this.keys={},this.mouseButtons={LEFT:null,MIDDLE:null,RIGHT:null},this.touches={ONE:null,TWO:null}}connect(e){if(e===void 0){console.warn("THREE.Controls: connect() now requires an element.");return}this.domElement!==null&&this.disconnect(),this.domElement=e}disconnect(){}dispose(){}update(){}};function cc(n,e,t,i){let s=Wp(i);switch(t){case Zl:return n*e;case Kl:return n*e/s.components*s.byteLength;case ja:return n*e/s.components*s.byteLength;case jl:return n*e*2/s.components*s.byteLength;case Qa:return n*e*2/s.components*s.byteLength;case Jl:return n*e*3/s.components*s.byteLength;case hn:return n*e*4/s.components*s.byteLength;case eo:return n*e*4/s.components*s.byteLength;case Tr:case Er:return Math.floor((n+3)/4)*Math.floor((e+3)/4)*8;case Ar:case Cr:return Math.floor((n+3)/4)*Math.floor((e+3)/4)*16;case no:case so:return Math.max(n,16)*Math.max(e,8)/4;case to:case io:return Math.max(n,8)*Math.max(e,8)/2;case ro:case ao:return Math.floor((n+3)/4)*Math.floor((e+3)/4)*8;case oo:return Math.floor((n+3)/4)*Math.floor((e+3)/4)*16;case lo:return Math.floor((n+3)/4)*Math.floor((e+3)/4)*16;case co:return Math.floor((n+4)/5)*Math.floor((e+3)/4)*16;case ho:return Math.floor((n+4)/5)*Math.floor((e+4)/5)*16;case uo:return Math.floor((n+5)/6)*Math.floor((e+4)/5)*16;case fo:return Math.floor((n+5)/6)*Math.floor((e+5)/6)*16;case po:return Math.floor((n+7)/8)*Math.floor((e+4)/5)*16;case mo:return Math.floor((n+7)/8)*Math.floor((e+5)/6)*16;case go:return Math.floor((n+7)/8)*Math.floor((e+7)/8)*16;case _o:return Math.floor((n+9)/10)*Math.floor((e+4)/5)*16;case xo:return Math.floor((n+9)/10)*Math.floor((e+5)/6)*16;case vo:return Math.floor((n+9)/10)*Math.floor((e+7)/8)*16;case yo:return Math.floor((n+9)/10)*Math.floor((e+9)/10)*16;case wo:return Math.floor((n+11)/12)*Math.floor((e+9)/10)*16;case bo:return Math.floor((n+11)/12)*Math.floor((e+11)/12)*16;case Mo:case So:case To:return Math.ceil(n/4)*Math.ceil(e/4)*16;case Eo:case Ao:return Math.ceil(n/4)*Math.ceil(e/4)*8;case Co:case Ro:return Math.ceil(n/4)*Math.ceil(e/4)*16}throw new Error(`Unable to determine texture byte length for ${t} format.`)}function Wp(n){switch(n){case vn:case Xl:return{byteLength:1,components:1};case vs:case ql:case ys:return{byteLength:2,components:1};case Ja:case Ka:return{byteLength:2,components:4};case mi:case Za:case Cn:return{byteLength:4,components:1};case Yl:case $l:return{byteLength:4,components:3}}throw new Error(`Unknown texture type ${n}.`)}typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("register",{detail:{revision:"180"}}));typeof window<"u"&&(window.__THREE__?console.warn("WARNING: Multiple instances of Three.js being imported."):window.__THREE__="180");function ud(){let n=null,e=!1,t=null,i=null;function s(r,a){t(r,a),i=n.requestAnimationFrame(s)}return{start:function(){e!==!0&&t!==null&&(i=n.requestAnimationFrame(s),e=!0)},stop:function(){n.cancelAnimationFrame(i),e=!1},setAnimationLoop:function(r){t=r},setContext:function(r){n=r}}}function qp(n){let e=new WeakMap;function t(o,c){let l=o.array,u=o.usage,h=l.byteLength,d=n.createBuffer();n.bindBuffer(c,d),n.bufferData(c,l,u),o.onUploadCallback();let f;if(l instanceof Float32Array)f=n.FLOAT;else if(typeof Float16Array<"u"&&l instanceof Float16Array)f=n.HALF_FLOAT;else if(l instanceof Uint16Array)o.isFloat16BufferAttribute?f=n.HALF_FLOAT:f=n.UNSIGNED_SHORT;else if(l instanceof Int16Array)f=n.SHORT;else if(l instanceof Uint32Array)f=n.UNSIGNED_INT;else if(l instanceof Int32Array)f=n.INT;else if(l instanceof Int8Array)f=n.BYTE;else if(l instanceof Uint8Array)f=n.UNSIGNED_BYTE;else if(l instanceof Uint8ClampedArray)f=n.UNSIGNED_BYTE;else throw new Error("THREE.WebGLAttributes: Unsupported buffer data format: "+l);return{buffer:d,type:f,bytesPerElement:l.BYTES_PER_ELEMENT,version:o.version,size:h}}function i(o,c,l){let u=c.array,h=c.updateRanges;if(n.bindBuffer(l,o),h.length===0)n.bufferSubData(l,0,u);else{h.sort((f,g)=>f.start-g.start);let d=0;for(let f=1;f<h.length;f++){let g=h[d],x=h[f];x.start<=g.start+g.count+1?g.count=Math.max(g.count,x.start+x.count-g.start):(++d,h[d]=x)}h.length=d+1;for(let f=0,g=h.length;f<g;f++){let x=h[f];n.bufferSubData(l,x.start*u.BYTES_PER_ELEMENT,u,x.start,x.count)}c.clearUpdateRanges()}c.onUploadCallback()}function s(o){return o.isInterleavedBufferAttribute&&(o=o.data),e.get(o)}function r(o){o.isInterleavedBufferAttribute&&(o=o.data);let c=e.get(o);c&&(n.deleteBuffer(c.buffer),e.delete(o))}function a(o,c){if(o.isInterleavedBufferAttribute&&(o=o.data),o.isGLBufferAttribute){let u=e.get(o);(!u||u.version<o.version)&&e.set(o,{buffer:o.buffer,type:o.type,bytesPerElement:o.elementSize,version:o.version});return}let l=e.get(o);if(l===void 0)e.set(o,t(o,c));else if(l.version<o.version){if(l.size!==o.array.byteLength)throw new Error("THREE.WebGLAttributes: The size of the buffer attribute's array buffer does not match the original size. Resizing buffer attributes is not supported.");i(l.buffer,o,c),l.version=o.version}}return{get:s,remove:r,update:a}}var Yp=`#ifdef USE_ALPHAHASH
	if ( diffuseColor.a < getAlphaHashThreshold( vPosition ) ) discard;
#endif`,$p=`#ifdef USE_ALPHAHASH
	const float ALPHA_HASH_SCALE = 0.05;
	float hash2D( vec2 value ) {
		return fract( 1.0e4 * sin( 17.0 * value.x + 0.1 * value.y ) * ( 0.1 + abs( sin( 13.0 * value.y + value.x ) ) ) );
	}
	float hash3D( vec3 value ) {
		return hash2D( vec2( hash2D( value.xy ), value.z ) );
	}
	float getAlphaHashThreshold( vec3 position ) {
		float maxDeriv = max(
			length( dFdx( position.xyz ) ),
			length( dFdy( position.xyz ) )
		);
		float pixScale = 1.0 / ( ALPHA_HASH_SCALE * maxDeriv );
		vec2 pixScales = vec2(
			exp2( floor( log2( pixScale ) ) ),
			exp2( ceil( log2( pixScale ) ) )
		);
		vec2 alpha = vec2(
			hash3D( floor( pixScales.x * position.xyz ) ),
			hash3D( floor( pixScales.y * position.xyz ) )
		);
		float lerpFactor = fract( log2( pixScale ) );
		float x = ( 1.0 - lerpFactor ) * alpha.x + lerpFactor * alpha.y;
		float a = min( lerpFactor, 1.0 - lerpFactor );
		vec3 cases = vec3(
			x * x / ( 2.0 * a * ( 1.0 - a ) ),
			( x - 0.5 * a ) / ( 1.0 - a ),
			1.0 - ( ( 1.0 - x ) * ( 1.0 - x ) / ( 2.0 * a * ( 1.0 - a ) ) )
		);
		float threshold = ( x < ( 1.0 - a ) )
			? ( ( x < a ) ? cases.x : cases.y )
			: cases.z;
		return clamp( threshold , 1.0e-6, 1.0 );
	}
#endif`,Zp=`#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, vAlphaMapUv ).g;
#endif`,Jp=`#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,Kp=`#ifdef USE_ALPHATEST
	#ifdef ALPHA_TO_COVERAGE
	diffuseColor.a = smoothstep( alphaTest, alphaTest + fwidth( diffuseColor.a ), diffuseColor.a );
	if ( diffuseColor.a == 0.0 ) discard;
	#else
	if ( diffuseColor.a < alphaTest ) discard;
	#endif
#endif`,jp=`#ifdef USE_ALPHATEST
	uniform float alphaTest;
#endif`,Qp=`#ifdef USE_AOMAP
	float ambientOcclusion = ( texture2D( aoMap, vAoMapUv ).r - 1.0 ) * aoMapIntensity + 1.0;
	reflectedLight.indirectDiffuse *= ambientOcclusion;
	#if defined( USE_CLEARCOAT ) 
		clearcoatSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_SHEEN ) 
		sheenSpecularIndirect *= ambientOcclusion;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD )
		float dotNV = saturate( dot( geometryNormal, geometryViewDir ) );
		reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNV, ambientOcclusion, material.roughness );
	#endif
#endif`,em=`#ifdef USE_AOMAP
	uniform sampler2D aoMap;
	uniform float aoMapIntensity;
#endif`,tm=`#ifdef USE_BATCHING
	#if ! defined( GL_ANGLE_multi_draw )
	#define gl_DrawID _gl_DrawID
	uniform int _gl_DrawID;
	#endif
	uniform highp sampler2D batchingTexture;
	uniform highp usampler2D batchingIdTexture;
	mat4 getBatchingMatrix( const in float i ) {
		int size = textureSize( batchingTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( batchingTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( batchingTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( batchingTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( batchingTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
	float getIndirectIndex( const in int i ) {
		int size = textureSize( batchingIdTexture, 0 ).x;
		int x = i % size;
		int y = i / size;
		return float( texelFetch( batchingIdTexture, ivec2( x, y ), 0 ).r );
	}
#endif
#ifdef USE_BATCHING_COLOR
	uniform sampler2D batchingColorTexture;
	vec3 getBatchingColor( const in float i ) {
		int size = textureSize( batchingColorTexture, 0 ).x;
		int j = int( i );
		int x = j % size;
		int y = j / size;
		return texelFetch( batchingColorTexture, ivec2( x, y ), 0 ).rgb;
	}
#endif`,nm=`#ifdef USE_BATCHING
	mat4 batchingMatrix = getBatchingMatrix( getIndirectIndex( gl_DrawID ) );
#endif`,im=`vec3 transformed = vec3( position );
#ifdef USE_ALPHAHASH
	vPosition = vec3( position );
#endif`,sm=`vec3 objectNormal = vec3( normal );
#ifdef USE_TANGENT
	vec3 objectTangent = vec3( tangent.xyz );
#endif`,rm=`float G_BlinnPhong_Implicit( ) {
	return 0.25;
}
float D_BlinnPhong( const in float shininess, const in float dotNH ) {
	return RECIPROCAL_PI * ( shininess * 0.5 + 1.0 ) * pow( dotNH, shininess );
}
vec3 BRDF_BlinnPhong( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in vec3 specularColor, const in float shininess ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( specularColor, 1.0, dotVH );
	float G = G_BlinnPhong_Implicit( );
	float D = D_BlinnPhong( shininess, dotNH );
	return F * ( G * D );
} // validated`,am=`#ifdef USE_IRIDESCENCE
	const mat3 XYZ_TO_REC709 = mat3(
		 3.2404542, -0.9692660,  0.0556434,
		-1.5371385,  1.8760108, -0.2040259,
		-0.4985314,  0.0415560,  1.0572252
	);
	vec3 Fresnel0ToIor( vec3 fresnel0 ) {
		vec3 sqrtF0 = sqrt( fresnel0 );
		return ( vec3( 1.0 ) + sqrtF0 ) / ( vec3( 1.0 ) - sqrtF0 );
	}
	vec3 IorToFresnel0( vec3 transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - vec3( incidentIor ) ) / ( transmittedIor + vec3( incidentIor ) ) );
	}
	float IorToFresnel0( float transmittedIor, float incidentIor ) {
		return pow2( ( transmittedIor - incidentIor ) / ( transmittedIor + incidentIor ));
	}
	vec3 evalSensitivity( float OPD, vec3 shift ) {
		float phase = 2.0 * PI * OPD * 1.0e-9;
		vec3 val = vec3( 5.4856e-13, 4.4201e-13, 5.2481e-13 );
		vec3 pos = vec3( 1.6810e+06, 1.7953e+06, 2.2084e+06 );
		vec3 var = vec3( 4.3278e+09, 9.3046e+09, 6.6121e+09 );
		vec3 xyz = val * sqrt( 2.0 * PI * var ) * cos( pos * phase + shift ) * exp( - pow2( phase ) * var );
		xyz.x += 9.7470e-14 * sqrt( 2.0 * PI * 4.5282e+09 ) * cos( 2.2399e+06 * phase + shift[ 0 ] ) * exp( - 4.5282e+09 * pow2( phase ) );
		xyz /= 1.0685e-7;
		vec3 rgb = XYZ_TO_REC709 * xyz;
		return rgb;
	}
	vec3 evalIridescence( float outsideIOR, float eta2, float cosTheta1, float thinFilmThickness, vec3 baseF0 ) {
		vec3 I;
		float iridescenceIOR = mix( outsideIOR, eta2, smoothstep( 0.0, 0.03, thinFilmThickness ) );
		float sinTheta2Sq = pow2( outsideIOR / iridescenceIOR ) * ( 1.0 - pow2( cosTheta1 ) );
		float cosTheta2Sq = 1.0 - sinTheta2Sq;
		if ( cosTheta2Sq < 0.0 ) {
			return vec3( 1.0 );
		}
		float cosTheta2 = sqrt( cosTheta2Sq );
		float R0 = IorToFresnel0( iridescenceIOR, outsideIOR );
		float R12 = F_Schlick( R0, 1.0, cosTheta1 );
		float T121 = 1.0 - R12;
		float phi12 = 0.0;
		if ( iridescenceIOR < outsideIOR ) phi12 = PI;
		float phi21 = PI - phi12;
		vec3 baseIOR = Fresnel0ToIor( clamp( baseF0, 0.0, 0.9999 ) );		vec3 R1 = IorToFresnel0( baseIOR, iridescenceIOR );
		vec3 R23 = F_Schlick( R1, 1.0, cosTheta2 );
		vec3 phi23 = vec3( 0.0 );
		if ( baseIOR[ 0 ] < iridescenceIOR ) phi23[ 0 ] = PI;
		if ( baseIOR[ 1 ] < iridescenceIOR ) phi23[ 1 ] = PI;
		if ( baseIOR[ 2 ] < iridescenceIOR ) phi23[ 2 ] = PI;
		float OPD = 2.0 * iridescenceIOR * thinFilmThickness * cosTheta2;
		vec3 phi = vec3( phi21 ) + phi23;
		vec3 R123 = clamp( R12 * R23, 1e-5, 0.9999 );
		vec3 r123 = sqrt( R123 );
		vec3 Rs = pow2( T121 ) * R23 / ( vec3( 1.0 ) - R123 );
		vec3 C0 = R12 + Rs;
		I = C0;
		vec3 Cm = Rs - T121;
		for ( int m = 1; m <= 2; ++ m ) {
			Cm *= r123;
			vec3 Sm = 2.0 * evalSensitivity( float( m ) * OPD, float( m ) * phi );
			I += Cm * Sm;
		}
		return max( I, vec3( 0.0 ) );
	}
#endif`,om=`#ifdef USE_BUMPMAP
	uniform sampler2D bumpMap;
	uniform float bumpScale;
	vec2 dHdxy_fwd() {
		vec2 dSTdx = dFdx( vBumpMapUv );
		vec2 dSTdy = dFdy( vBumpMapUv );
		float Hll = bumpScale * texture2D( bumpMap, vBumpMapUv ).x;
		float dBx = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdx ).x - Hll;
		float dBy = bumpScale * texture2D( bumpMap, vBumpMapUv + dSTdy ).x - Hll;
		return vec2( dBx, dBy );
	}
	vec3 perturbNormalArb( vec3 surf_pos, vec3 surf_norm, vec2 dHdxy, float faceDirection ) {
		vec3 vSigmaX = normalize( dFdx( surf_pos.xyz ) );
		vec3 vSigmaY = normalize( dFdy( surf_pos.xyz ) );
		vec3 vN = surf_norm;
		vec3 R1 = cross( vSigmaY, vN );
		vec3 R2 = cross( vN, vSigmaX );
		float fDet = dot( vSigmaX, R1 ) * faceDirection;
		vec3 vGrad = sign( fDet ) * ( dHdxy.x * R1 + dHdxy.y * R2 );
		return normalize( abs( fDet ) * surf_norm - vGrad );
	}
#endif`,lm=`#if NUM_CLIPPING_PLANES > 0
	vec4 plane;
	#ifdef ALPHA_TO_COVERAGE
		float distanceToPlane, distanceGradient;
		float clipOpacity = 1.0;
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
			distanceGradient = fwidth( distanceToPlane ) / 2.0;
			clipOpacity *= smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			if ( clipOpacity == 0.0 ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			float unionClipOpacity = 1.0;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				distanceToPlane = - dot( vClipPosition, plane.xyz ) + plane.w;
				distanceGradient = fwidth( distanceToPlane ) / 2.0;
				unionClipOpacity *= 1.0 - smoothstep( - distanceGradient, distanceGradient, distanceToPlane );
			}
			#pragma unroll_loop_end
			clipOpacity *= 1.0 - unionClipOpacity;
		#endif
		diffuseColor.a *= clipOpacity;
		if ( diffuseColor.a == 0.0 ) discard;
	#else
		#pragma unroll_loop_start
		for ( int i = 0; i < UNION_CLIPPING_PLANES; i ++ ) {
			plane = clippingPlanes[ i ];
			if ( dot( vClipPosition, plane.xyz ) > plane.w ) discard;
		}
		#pragma unroll_loop_end
		#if UNION_CLIPPING_PLANES < NUM_CLIPPING_PLANES
			bool clipped = true;
			#pragma unroll_loop_start
			for ( int i = UNION_CLIPPING_PLANES; i < NUM_CLIPPING_PLANES; i ++ ) {
				plane = clippingPlanes[ i ];
				clipped = ( dot( vClipPosition, plane.xyz ) > plane.w ) && clipped;
			}
			#pragma unroll_loop_end
			if ( clipped ) discard;
		#endif
	#endif
#endif`,cm=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
	uniform vec4 clippingPlanes[ NUM_CLIPPING_PLANES ];
#endif`,hm=`#if NUM_CLIPPING_PLANES > 0
	varying vec3 vClipPosition;
#endif`,um=`#if NUM_CLIPPING_PLANES > 0
	vClipPosition = - mvPosition.xyz;
#endif`,dm=`#if defined( USE_COLOR_ALPHA )
	diffuseColor *= vColor;
#elif defined( USE_COLOR )
	diffuseColor.rgb *= vColor;
#endif`,fm=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR )
	varying vec3 vColor;
#endif`,pm=`#if defined( USE_COLOR_ALPHA )
	varying vec4 vColor;
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	varying vec3 vColor;
#endif`,mm=`#if defined( USE_COLOR_ALPHA )
	vColor = vec4( 1.0 );
#elif defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR ) || defined( USE_BATCHING_COLOR )
	vColor = vec3( 1.0 );
#endif
#ifdef USE_COLOR
	vColor *= color;
#endif
#ifdef USE_INSTANCING_COLOR
	vColor.xyz *= instanceColor.xyz;
#endif
#ifdef USE_BATCHING_COLOR
	vec3 batchingColor = getBatchingColor( getIndirectIndex( gl_DrawID ) );
	vColor.xyz *= batchingColor.xyz;
#endif`,gm=`#define PI 3.141592653589793
#define PI2 6.283185307179586
#define PI_HALF 1.5707963267948966
#define RECIPROCAL_PI 0.3183098861837907
#define RECIPROCAL_PI2 0.15915494309189535
#define EPSILON 1e-6
#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
#define whiteComplement( a ) ( 1.0 - saturate( a ) )
float pow2( const in float x ) { return x*x; }
vec3 pow2( const in vec3 x ) { return x*x; }
float pow3( const in float x ) { return x*x*x; }
float pow4( const in float x ) { float x2 = x*x; return x2*x2; }
float max3( const in vec3 v ) { return max( max( v.x, v.y ), v.z ); }
float average( const in vec3 v ) { return dot( v, vec3( 0.3333333 ) ); }
highp float rand( const in vec2 uv ) {
	const highp float a = 12.9898, b = 78.233, c = 43758.5453;
	highp float dt = dot( uv.xy, vec2( a,b ) ), sn = mod( dt, PI );
	return fract( sin( sn ) * c );
}
#ifdef HIGH_PRECISION
	float precisionSafeLength( vec3 v ) { return length( v ); }
#else
	float precisionSafeLength( vec3 v ) {
		float maxComponent = max3( abs( v ) );
		return length( v / maxComponent ) * maxComponent;
	}
#endif
struct IncidentLight {
	vec3 color;
	vec3 direction;
	bool visible;
};
struct ReflectedLight {
	vec3 directDiffuse;
	vec3 directSpecular;
	vec3 indirectDiffuse;
	vec3 indirectSpecular;
};
#ifdef USE_ALPHAHASH
	varying vec3 vPosition;
#endif
vec3 transformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( matrix * vec4( dir, 0.0 ) ).xyz );
}
vec3 inverseTransformDirection( in vec3 dir, in mat4 matrix ) {
	return normalize( ( vec4( dir, 0.0 ) * matrix ).xyz );
}
mat3 transposeMat3( const in mat3 m ) {
	mat3 tmp;
	tmp[ 0 ] = vec3( m[ 0 ].x, m[ 1 ].x, m[ 2 ].x );
	tmp[ 1 ] = vec3( m[ 0 ].y, m[ 1 ].y, m[ 2 ].y );
	tmp[ 2 ] = vec3( m[ 0 ].z, m[ 1 ].z, m[ 2 ].z );
	return tmp;
}
bool isPerspectiveMatrix( mat4 m ) {
	return m[ 2 ][ 3 ] == - 1.0;
}
vec2 equirectUv( in vec3 dir ) {
	float u = atan( dir.z, dir.x ) * RECIPROCAL_PI2 + 0.5;
	float v = asin( clamp( dir.y, - 1.0, 1.0 ) ) * RECIPROCAL_PI + 0.5;
	return vec2( u, v );
}
vec3 BRDF_Lambert( const in vec3 diffuseColor ) {
	return RECIPROCAL_PI * diffuseColor;
}
vec3 F_Schlick( const in vec3 f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
}
float F_Schlick( const in float f0, const in float f90, const in float dotVH ) {
	float fresnel = exp2( ( - 5.55473 * dotVH - 6.98316 ) * dotVH );
	return f0 * ( 1.0 - fresnel ) + ( f90 * fresnel );
} // validated`,_m=`#ifdef ENVMAP_TYPE_CUBE_UV
	#define cubeUV_minMipLevel 4.0
	#define cubeUV_minTileSize 16.0
	float getFace( vec3 direction ) {
		vec3 absDirection = abs( direction );
		float face = - 1.0;
		if ( absDirection.x > absDirection.z ) {
			if ( absDirection.x > absDirection.y )
				face = direction.x > 0.0 ? 0.0 : 3.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		} else {
			if ( absDirection.z > absDirection.y )
				face = direction.z > 0.0 ? 2.0 : 5.0;
			else
				face = direction.y > 0.0 ? 1.0 : 4.0;
		}
		return face;
	}
	vec2 getUV( vec3 direction, float face ) {
		vec2 uv;
		if ( face == 0.0 ) {
			uv = vec2( direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 1.0 ) {
			uv = vec2( - direction.x, - direction.z ) / abs( direction.y );
		} else if ( face == 2.0 ) {
			uv = vec2( - direction.x, direction.y ) / abs( direction.z );
		} else if ( face == 3.0 ) {
			uv = vec2( - direction.z, direction.y ) / abs( direction.x );
		} else if ( face == 4.0 ) {
			uv = vec2( - direction.x, direction.z ) / abs( direction.y );
		} else {
			uv = vec2( direction.x, direction.y ) / abs( direction.z );
		}
		return 0.5 * ( uv + 1.0 );
	}
	vec3 bilinearCubeUV( sampler2D envMap, vec3 direction, float mipInt ) {
		float face = getFace( direction );
		float filterInt = max( cubeUV_minMipLevel - mipInt, 0.0 );
		mipInt = max( mipInt, cubeUV_minMipLevel );
		float faceSize = exp2( mipInt );
		highp vec2 uv = getUV( direction, face ) * ( faceSize - 2.0 ) + 1.0;
		if ( face > 2.0 ) {
			uv.y += faceSize;
			face -= 3.0;
		}
		uv.x += face * faceSize;
		uv.x += filterInt * 3.0 * cubeUV_minTileSize;
		uv.y += 4.0 * ( exp2( CUBEUV_MAX_MIP ) - faceSize );
		uv.x *= CUBEUV_TEXEL_WIDTH;
		uv.y *= CUBEUV_TEXEL_HEIGHT;
		#ifdef texture2DGradEXT
			return texture2DGradEXT( envMap, uv, vec2( 0.0 ), vec2( 0.0 ) ).rgb;
		#else
			return texture2D( envMap, uv ).rgb;
		#endif
	}
	#define cubeUV_r0 1.0
	#define cubeUV_m0 - 2.0
	#define cubeUV_r1 0.8
	#define cubeUV_m1 - 1.0
	#define cubeUV_r4 0.4
	#define cubeUV_m4 2.0
	#define cubeUV_r5 0.305
	#define cubeUV_m5 3.0
	#define cubeUV_r6 0.21
	#define cubeUV_m6 4.0
	float roughnessToMip( float roughness ) {
		float mip = 0.0;
		if ( roughness >= cubeUV_r1 ) {
			mip = ( cubeUV_r0 - roughness ) * ( cubeUV_m1 - cubeUV_m0 ) / ( cubeUV_r0 - cubeUV_r1 ) + cubeUV_m0;
		} else if ( roughness >= cubeUV_r4 ) {
			mip = ( cubeUV_r1 - roughness ) * ( cubeUV_m4 - cubeUV_m1 ) / ( cubeUV_r1 - cubeUV_r4 ) + cubeUV_m1;
		} else if ( roughness >= cubeUV_r5 ) {
			mip = ( cubeUV_r4 - roughness ) * ( cubeUV_m5 - cubeUV_m4 ) / ( cubeUV_r4 - cubeUV_r5 ) + cubeUV_m4;
		} else if ( roughness >= cubeUV_r6 ) {
			mip = ( cubeUV_r5 - roughness ) * ( cubeUV_m6 - cubeUV_m5 ) / ( cubeUV_r5 - cubeUV_r6 ) + cubeUV_m5;
		} else {
			mip = - 2.0 * log2( 1.16 * roughness );		}
		return mip;
	}
	vec4 textureCubeUV( sampler2D envMap, vec3 sampleDir, float roughness ) {
		float mip = clamp( roughnessToMip( roughness ), cubeUV_m0, CUBEUV_MAX_MIP );
		float mipF = fract( mip );
		float mipInt = floor( mip );
		vec3 color0 = bilinearCubeUV( envMap, sampleDir, mipInt );
		if ( mipF == 0.0 ) {
			return vec4( color0, 1.0 );
		} else {
			vec3 color1 = bilinearCubeUV( envMap, sampleDir, mipInt + 1.0 );
			return vec4( mix( color0, color1, mipF ), 1.0 );
		}
	}
#endif`,xm=`vec3 transformedNormal = objectNormal;
#ifdef USE_TANGENT
	vec3 transformedTangent = objectTangent;
#endif
#ifdef USE_BATCHING
	mat3 bm = mat3( batchingMatrix );
	transformedNormal /= vec3( dot( bm[ 0 ], bm[ 0 ] ), dot( bm[ 1 ], bm[ 1 ] ), dot( bm[ 2 ], bm[ 2 ] ) );
	transformedNormal = bm * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = bm * transformedTangent;
	#endif
#endif
#ifdef USE_INSTANCING
	mat3 im = mat3( instanceMatrix );
	transformedNormal /= vec3( dot( im[ 0 ], im[ 0 ] ), dot( im[ 1 ], im[ 1 ] ), dot( im[ 2 ], im[ 2 ] ) );
	transformedNormal = im * transformedNormal;
	#ifdef USE_TANGENT
		transformedTangent = im * transformedTangent;
	#endif
#endif
transformedNormal = normalMatrix * transformedNormal;
#ifdef FLIP_SIDED
	transformedNormal = - transformedNormal;
#endif
#ifdef USE_TANGENT
	transformedTangent = ( modelViewMatrix * vec4( transformedTangent, 0.0 ) ).xyz;
	#ifdef FLIP_SIDED
		transformedTangent = - transformedTangent;
	#endif
#endif`,vm=`#ifdef USE_DISPLACEMENTMAP
	uniform sampler2D displacementMap;
	uniform float displacementScale;
	uniform float displacementBias;
#endif`,ym=`#ifdef USE_DISPLACEMENTMAP
	transformed += normalize( objectNormal ) * ( texture2D( displacementMap, vDisplacementMapUv ).x * displacementScale + displacementBias );
#endif`,wm=`#ifdef USE_EMISSIVEMAP
	vec4 emissiveColor = texture2D( emissiveMap, vEmissiveMapUv );
	#ifdef DECODE_VIDEO_TEXTURE_EMISSIVE
		emissiveColor = sRGBTransferEOTF( emissiveColor );
	#endif
	totalEmissiveRadiance *= emissiveColor.rgb;
#endif`,bm=`#ifdef USE_EMISSIVEMAP
	uniform sampler2D emissiveMap;
#endif`,Mm="gl_FragColor = linearToOutputTexel( gl_FragColor );",Sm=`vec4 LinearTransferOETF( in vec4 value ) {
	return value;
}
vec4 sRGBTransferEOTF( in vec4 value ) {
	return vec4( mix( pow( value.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), value.rgb * 0.0773993808, vec3( lessThanEqual( value.rgb, vec3( 0.04045 ) ) ) ), value.a );
}
vec4 sRGBTransferOETF( in vec4 value ) {
	return vec4( mix( pow( value.rgb, vec3( 0.41666 ) ) * 1.055 - vec3( 0.055 ), value.rgb * 12.92, vec3( lessThanEqual( value.rgb, vec3( 0.0031308 ) ) ) ), value.a );
}`,Tm=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vec3 cameraToFrag;
		if ( isOrthographic ) {
			cameraToFrag = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToFrag = normalize( vWorldPosition - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vec3 reflectVec = reflect( cameraToFrag, worldNormal );
		#else
			vec3 reflectVec = refract( cameraToFrag, worldNormal, refractionRatio );
		#endif
	#else
		vec3 reflectVec = vReflect;
	#endif
	#ifdef ENVMAP_TYPE_CUBE
		vec4 envColor = textureCube( envMap, envMapRotation * vec3( flipEnvMap * reflectVec.x, reflectVec.yz ) );
	#else
		vec4 envColor = vec4( 0.0 );
	#endif
	#ifdef ENVMAP_BLENDING_MULTIPLY
		outgoingLight = mix( outgoingLight, outgoingLight * envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_MIX )
		outgoingLight = mix( outgoingLight, envColor.xyz, specularStrength * reflectivity );
	#elif defined( ENVMAP_BLENDING_ADD )
		outgoingLight += envColor.xyz * specularStrength * reflectivity;
	#endif
#endif`,Em=`#ifdef USE_ENVMAP
	uniform float envMapIntensity;
	uniform float flipEnvMap;
	uniform mat3 envMapRotation;
	#ifdef ENVMAP_TYPE_CUBE
		uniform samplerCube envMap;
	#else
		uniform sampler2D envMap;
	#endif
	
#endif`,Am=`#ifdef USE_ENVMAP
	uniform float reflectivity;
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		varying vec3 vWorldPosition;
		uniform float refractionRatio;
	#else
		varying vec3 vReflect;
	#endif
#endif`,Cm=`#ifdef USE_ENVMAP
	#if defined( USE_BUMPMAP ) || defined( USE_NORMALMAP ) || defined( PHONG ) || defined( LAMBERT )
		#define ENV_WORLDPOS
	#endif
	#ifdef ENV_WORLDPOS
		
		varying vec3 vWorldPosition;
	#else
		varying vec3 vReflect;
		uniform float refractionRatio;
	#endif
#endif`,Rm=`#ifdef USE_ENVMAP
	#ifdef ENV_WORLDPOS
		vWorldPosition = worldPosition.xyz;
	#else
		vec3 cameraToVertex;
		if ( isOrthographic ) {
			cameraToVertex = normalize( vec3( - viewMatrix[ 0 ][ 2 ], - viewMatrix[ 1 ][ 2 ], - viewMatrix[ 2 ][ 2 ] ) );
		} else {
			cameraToVertex = normalize( worldPosition.xyz - cameraPosition );
		}
		vec3 worldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
		#ifdef ENVMAP_MODE_REFLECTION
			vReflect = reflect( cameraToVertex, worldNormal );
		#else
			vReflect = refract( cameraToVertex, worldNormal, refractionRatio );
		#endif
	#endif
#endif`,Pm=`#ifdef USE_FOG
	vFogDepth = - mvPosition.z;
#endif`,Im=`#ifdef USE_FOG
	varying float vFogDepth;
#endif`,Nm=`#ifdef USE_FOG
	#ifdef FOG_EXP2
		float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
	#else
		float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
	#endif
	gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
#endif`,Dm=`#ifdef USE_FOG
	uniform vec3 fogColor;
	varying float vFogDepth;
	#ifdef FOG_EXP2
		uniform float fogDensity;
	#else
		uniform float fogNear;
		uniform float fogFar;
	#endif
#endif`,Lm=`#ifdef USE_GRADIENTMAP
	uniform sampler2D gradientMap;
#endif
vec3 getGradientIrradiance( vec3 normal, vec3 lightDirection ) {
	float dotNL = dot( normal, lightDirection );
	vec2 coord = vec2( dotNL * 0.5 + 0.5, 0.0 );
	#ifdef USE_GRADIENTMAP
		return vec3( texture2D( gradientMap, coord ).r );
	#else
		vec2 fw = fwidth( coord ) * 0.5;
		return mix( vec3( 0.7 ), vec3( 1.0 ), smoothstep( 0.7 - fw.x, 0.7 + fw.x, coord.x ) );
	#endif
}`,Um=`#ifdef USE_LIGHTMAP
	uniform sampler2D lightMap;
	uniform float lightMapIntensity;
#endif`,Fm=`LambertMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularStrength = specularStrength;`,Om=`varying vec3 vViewPosition;
struct LambertMaterial {
	vec3 diffuseColor;
	float specularStrength;
};
void RE_Direct_Lambert( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Lambert( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in LambertMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Lambert
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Lambert`,km=`uniform bool receiveShadow;
uniform vec3 ambientLightColor;
#if defined( USE_LIGHT_PROBES )
	uniform vec3 lightProbe[ 9 ];
#endif
vec3 shGetIrradianceAt( in vec3 normal, in vec3 shCoefficients[ 9 ] ) {
	float x = normal.x, y = normal.y, z = normal.z;
	vec3 result = shCoefficients[ 0 ] * 0.886227;
	result += shCoefficients[ 1 ] * 2.0 * 0.511664 * y;
	result += shCoefficients[ 2 ] * 2.0 * 0.511664 * z;
	result += shCoefficients[ 3 ] * 2.0 * 0.511664 * x;
	result += shCoefficients[ 4 ] * 2.0 * 0.429043 * x * y;
	result += shCoefficients[ 5 ] * 2.0 * 0.429043 * y * z;
	result += shCoefficients[ 6 ] * ( 0.743125 * z * z - 0.247708 );
	result += shCoefficients[ 7 ] * 2.0 * 0.429043 * x * z;
	result += shCoefficients[ 8 ] * 0.429043 * ( x * x - y * y );
	return result;
}
vec3 getLightProbeIrradiance( const in vec3 lightProbe[ 9 ], const in vec3 normal ) {
	vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
	vec3 irradiance = shGetIrradianceAt( worldNormal, lightProbe );
	return irradiance;
}
vec3 getAmbientLightIrradiance( const in vec3 ambientLightColor ) {
	vec3 irradiance = ambientLightColor;
	return irradiance;
}
float getDistanceAttenuation( const in float lightDistance, const in float cutoffDistance, const in float decayExponent ) {
	float distanceFalloff = 1.0 / max( pow( lightDistance, decayExponent ), 0.01 );
	if ( cutoffDistance > 0.0 ) {
		distanceFalloff *= pow2( saturate( 1.0 - pow4( lightDistance / cutoffDistance ) ) );
	}
	return distanceFalloff;
}
float getSpotAttenuation( const in float coneCosine, const in float penumbraCosine, const in float angleCosine ) {
	return smoothstep( coneCosine, penumbraCosine, angleCosine );
}
#if NUM_DIR_LIGHTS > 0
	struct DirectionalLight {
		vec3 direction;
		vec3 color;
	};
	uniform DirectionalLight directionalLights[ NUM_DIR_LIGHTS ];
	void getDirectionalLightInfo( const in DirectionalLight directionalLight, out IncidentLight light ) {
		light.color = directionalLight.color;
		light.direction = directionalLight.direction;
		light.visible = true;
	}
#endif
#if NUM_POINT_LIGHTS > 0
	struct PointLight {
		vec3 position;
		vec3 color;
		float distance;
		float decay;
	};
	uniform PointLight pointLights[ NUM_POINT_LIGHTS ];
	void getPointLightInfo( const in PointLight pointLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = pointLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float lightDistance = length( lVector );
		light.color = pointLight.color;
		light.color *= getDistanceAttenuation( lightDistance, pointLight.distance, pointLight.decay );
		light.visible = ( light.color != vec3( 0.0 ) );
	}
#endif
#if NUM_SPOT_LIGHTS > 0
	struct SpotLight {
		vec3 position;
		vec3 direction;
		vec3 color;
		float distance;
		float decay;
		float coneCos;
		float penumbraCos;
	};
	uniform SpotLight spotLights[ NUM_SPOT_LIGHTS ];
	void getSpotLightInfo( const in SpotLight spotLight, const in vec3 geometryPosition, out IncidentLight light ) {
		vec3 lVector = spotLight.position - geometryPosition;
		light.direction = normalize( lVector );
		float angleCos = dot( light.direction, spotLight.direction );
		float spotAttenuation = getSpotAttenuation( spotLight.coneCos, spotLight.penumbraCos, angleCos );
		if ( spotAttenuation > 0.0 ) {
			float lightDistance = length( lVector );
			light.color = spotLight.color * spotAttenuation;
			light.color *= getDistanceAttenuation( lightDistance, spotLight.distance, spotLight.decay );
			light.visible = ( light.color != vec3( 0.0 ) );
		} else {
			light.color = vec3( 0.0 );
			light.visible = false;
		}
	}
#endif
#if NUM_RECT_AREA_LIGHTS > 0
	struct RectAreaLight {
		vec3 color;
		vec3 position;
		vec3 halfWidth;
		vec3 halfHeight;
	};
	uniform sampler2D ltc_1;	uniform sampler2D ltc_2;
	uniform RectAreaLight rectAreaLights[ NUM_RECT_AREA_LIGHTS ];
#endif
#if NUM_HEMI_LIGHTS > 0
	struct HemisphereLight {
		vec3 direction;
		vec3 skyColor;
		vec3 groundColor;
	};
	uniform HemisphereLight hemisphereLights[ NUM_HEMI_LIGHTS ];
	vec3 getHemisphereLightIrradiance( const in HemisphereLight hemiLight, const in vec3 normal ) {
		float dotNL = dot( normal, hemiLight.direction );
		float hemiDiffuseWeight = 0.5 * dotNL + 0.5;
		vec3 irradiance = mix( hemiLight.groundColor, hemiLight.skyColor, hemiDiffuseWeight );
		return irradiance;
	}
#endif`,Bm=`#ifdef USE_ENVMAP
	vec3 getIBLIrradiance( const in vec3 normal ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 worldNormal = inverseTransformDirection( normal, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * worldNormal, 1.0 );
			return PI * envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	vec3 getIBLRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness ) {
		#ifdef ENVMAP_TYPE_CUBE_UV
			vec3 reflectVec = reflect( - viewDir, normal );
			reflectVec = normalize( mix( reflectVec, normal, roughness * roughness) );
			reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
			vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );
			return envMapColor.rgb * envMapIntensity;
		#else
			return vec3( 0.0 );
		#endif
	}
	#ifdef USE_ANISOTROPY
		vec3 getIBLAnisotropyRadiance( const in vec3 viewDir, const in vec3 normal, const in float roughness, const in vec3 bitangent, const in float anisotropy ) {
			#ifdef ENVMAP_TYPE_CUBE_UV
				vec3 bentNormal = cross( bitangent, viewDir );
				bentNormal = normalize( cross( bentNormal, bitangent ) );
				bentNormal = normalize( mix( bentNormal, normal, pow2( pow2( 1.0 - anisotropy * ( 1.0 - roughness ) ) ) ) );
				return getIBLRadiance( viewDir, bentNormal, roughness );
			#else
				return vec3( 0.0 );
			#endif
		}
	#endif
#endif`,zm=`ToonMaterial material;
material.diffuseColor = diffuseColor.rgb;`,Vm=`varying vec3 vViewPosition;
struct ToonMaterial {
	vec3 diffuseColor;
};
void RE_Direct_Toon( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	vec3 irradiance = getGradientIrradiance( geometryNormal, directLight.direction ) * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Toon( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in ToonMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_Toon
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Toon`,Hm=`BlinnPhongMaterial material;
material.diffuseColor = diffuseColor.rgb;
material.specularColor = specular;
material.specularShininess = shininess;
material.specularStrength = specularStrength;`,Gm=`varying vec3 vViewPosition;
struct BlinnPhongMaterial {
	vec3 diffuseColor;
	vec3 specularColor;
	float specularShininess;
	float specularStrength;
};
void RE_Direct_BlinnPhong( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
	reflectedLight.directSpecular += irradiance * BRDF_BlinnPhong( directLight.direction, geometryViewDir, geometryNormal, material.specularColor, material.specularShininess ) * material.specularStrength;
}
void RE_IndirectDiffuse_BlinnPhong( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in BlinnPhongMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
#define RE_Direct				RE_Direct_BlinnPhong
#define RE_IndirectDiffuse		RE_IndirectDiffuse_BlinnPhong`,Wm=`PhysicalMaterial material;
material.diffuseColor = diffuseColor.rgb * ( 1.0 - metalnessFactor );
vec3 dxy = max( abs( dFdx( nonPerturbedNormal ) ), abs( dFdy( nonPerturbedNormal ) ) );
float geometryRoughness = max( max( dxy.x, dxy.y ), dxy.z );
material.roughness = max( roughnessFactor, 0.0525 );material.roughness += geometryRoughness;
material.roughness = min( material.roughness, 1.0 );
#ifdef IOR
	material.ior = ior;
	#ifdef USE_SPECULAR
		float specularIntensityFactor = specularIntensity;
		vec3 specularColorFactor = specularColor;
		#ifdef USE_SPECULAR_COLORMAP
			specularColorFactor *= texture2D( specularColorMap, vSpecularColorMapUv ).rgb;
		#endif
		#ifdef USE_SPECULAR_INTENSITYMAP
			specularIntensityFactor *= texture2D( specularIntensityMap, vSpecularIntensityMapUv ).a;
		#endif
		material.specularF90 = mix( specularIntensityFactor, 1.0, metalnessFactor );
	#else
		float specularIntensityFactor = 1.0;
		vec3 specularColorFactor = vec3( 1.0 );
		material.specularF90 = 1.0;
	#endif
	material.specularColor = mix( min( pow2( ( material.ior - 1.0 ) / ( material.ior + 1.0 ) ) * specularColorFactor, vec3( 1.0 ) ) * specularIntensityFactor, diffuseColor.rgb, metalnessFactor );
#else
	material.specularColor = mix( vec3( 0.04 ), diffuseColor.rgb, metalnessFactor );
	material.specularF90 = 1.0;
#endif
#ifdef USE_CLEARCOAT
	material.clearcoat = clearcoat;
	material.clearcoatRoughness = clearcoatRoughness;
	material.clearcoatF0 = vec3( 0.04 );
	material.clearcoatF90 = 1.0;
	#ifdef USE_CLEARCOATMAP
		material.clearcoat *= texture2D( clearcoatMap, vClearcoatMapUv ).x;
	#endif
	#ifdef USE_CLEARCOAT_ROUGHNESSMAP
		material.clearcoatRoughness *= texture2D( clearcoatRoughnessMap, vClearcoatRoughnessMapUv ).y;
	#endif
	material.clearcoat = saturate( material.clearcoat );	material.clearcoatRoughness = max( material.clearcoatRoughness, 0.0525 );
	material.clearcoatRoughness += geometryRoughness;
	material.clearcoatRoughness = min( material.clearcoatRoughness, 1.0 );
#endif
#ifdef USE_DISPERSION
	material.dispersion = dispersion;
#endif
#ifdef USE_IRIDESCENCE
	material.iridescence = iridescence;
	material.iridescenceIOR = iridescenceIOR;
	#ifdef USE_IRIDESCENCEMAP
		material.iridescence *= texture2D( iridescenceMap, vIridescenceMapUv ).r;
	#endif
	#ifdef USE_IRIDESCENCE_THICKNESSMAP
		material.iridescenceThickness = (iridescenceThicknessMaximum - iridescenceThicknessMinimum) * texture2D( iridescenceThicknessMap, vIridescenceThicknessMapUv ).g + iridescenceThicknessMinimum;
	#else
		material.iridescenceThickness = iridescenceThicknessMaximum;
	#endif
#endif
#ifdef USE_SHEEN
	material.sheenColor = sheenColor;
	#ifdef USE_SHEEN_COLORMAP
		material.sheenColor *= texture2D( sheenColorMap, vSheenColorMapUv ).rgb;
	#endif
	material.sheenRoughness = clamp( sheenRoughness, 0.07, 1.0 );
	#ifdef USE_SHEEN_ROUGHNESSMAP
		material.sheenRoughness *= texture2D( sheenRoughnessMap, vSheenRoughnessMapUv ).a;
	#endif
#endif
#ifdef USE_ANISOTROPY
	#ifdef USE_ANISOTROPYMAP
		mat2 anisotropyMat = mat2( anisotropyVector.x, anisotropyVector.y, - anisotropyVector.y, anisotropyVector.x );
		vec3 anisotropyPolar = texture2D( anisotropyMap, vAnisotropyMapUv ).rgb;
		vec2 anisotropyV = anisotropyMat * normalize( 2.0 * anisotropyPolar.rg - vec2( 1.0 ) ) * anisotropyPolar.b;
	#else
		vec2 anisotropyV = anisotropyVector;
	#endif
	material.anisotropy = length( anisotropyV );
	if( material.anisotropy == 0.0 ) {
		anisotropyV = vec2( 1.0, 0.0 );
	} else {
		anisotropyV /= material.anisotropy;
		material.anisotropy = saturate( material.anisotropy );
	}
	material.alphaT = mix( pow2( material.roughness ), 1.0, pow2( material.anisotropy ) );
	material.anisotropyT = tbn[ 0 ] * anisotropyV.x + tbn[ 1 ] * anisotropyV.y;
	material.anisotropyB = tbn[ 1 ] * anisotropyV.x - tbn[ 0 ] * anisotropyV.y;
#endif`,Xm=`struct PhysicalMaterial {
	vec3 diffuseColor;
	float roughness;
	vec3 specularColor;
	float specularF90;
	float dispersion;
	#ifdef USE_CLEARCOAT
		float clearcoat;
		float clearcoatRoughness;
		vec3 clearcoatF0;
		float clearcoatF90;
	#endif
	#ifdef USE_IRIDESCENCE
		float iridescence;
		float iridescenceIOR;
		float iridescenceThickness;
		vec3 iridescenceFresnel;
		vec3 iridescenceF0;
	#endif
	#ifdef USE_SHEEN
		vec3 sheenColor;
		float sheenRoughness;
	#endif
	#ifdef IOR
		float ior;
	#endif
	#ifdef USE_TRANSMISSION
		float transmission;
		float transmissionAlpha;
		float thickness;
		float attenuationDistance;
		vec3 attenuationColor;
	#endif
	#ifdef USE_ANISOTROPY
		float anisotropy;
		float alphaT;
		vec3 anisotropyT;
		vec3 anisotropyB;
	#endif
};
vec3 clearcoatSpecularDirect = vec3( 0.0 );
vec3 clearcoatSpecularIndirect = vec3( 0.0 );
vec3 sheenSpecularDirect = vec3( 0.0 );
vec3 sheenSpecularIndirect = vec3(0.0 );
vec3 Schlick_to_F0( const in vec3 f, const in float f90, const in float dotVH ) {
    float x = clamp( 1.0 - dotVH, 0.0, 1.0 );
    float x2 = x * x;
    float x5 = clamp( x * x2 * x2, 0.0, 0.9999 );
    return ( f - vec3( f90 ) * x5 ) / ( 1.0 - x5 );
}
float V_GGX_SmithCorrelated( const in float alpha, const in float dotNL, const in float dotNV ) {
	float a2 = pow2( alpha );
	float gv = dotNL * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNV ) );
	float gl = dotNV * sqrt( a2 + ( 1.0 - a2 ) * pow2( dotNL ) );
	return 0.5 / max( gv + gl, EPSILON );
}
float D_GGX( const in float alpha, const in float dotNH ) {
	float a2 = pow2( alpha );
	float denom = pow2( dotNH ) * ( a2 - 1.0 ) + 1.0;
	return RECIPROCAL_PI * a2 / pow2( denom );
}
#ifdef USE_ANISOTROPY
	float V_GGX_SmithCorrelated_Anisotropic( const in float alphaT, const in float alphaB, const in float dotTV, const in float dotBV, const in float dotTL, const in float dotBL, const in float dotNV, const in float dotNL ) {
		float gv = dotNL * length( vec3( alphaT * dotTV, alphaB * dotBV, dotNV ) );
		float gl = dotNV * length( vec3( alphaT * dotTL, alphaB * dotBL, dotNL ) );
		float v = 0.5 / ( gv + gl );
		return saturate(v);
	}
	float D_GGX_Anisotropic( const in float alphaT, const in float alphaB, const in float dotNH, const in float dotTH, const in float dotBH ) {
		float a2 = alphaT * alphaB;
		highp vec3 v = vec3( alphaB * dotTH, alphaT * dotBH, a2 * dotNH );
		highp float v2 = dot( v, v );
		float w2 = a2 / v2;
		return RECIPROCAL_PI * a2 * pow2 ( w2 );
	}
#endif
#ifdef USE_CLEARCOAT
	vec3 BRDF_GGX_Clearcoat( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material) {
		vec3 f0 = material.clearcoatF0;
		float f90 = material.clearcoatF90;
		float roughness = material.clearcoatRoughness;
		float alpha = pow2( roughness );
		vec3 halfDir = normalize( lightDir + viewDir );
		float dotNL = saturate( dot( normal, lightDir ) );
		float dotNV = saturate( dot( normal, viewDir ) );
		float dotNH = saturate( dot( normal, halfDir ) );
		float dotVH = saturate( dot( viewDir, halfDir ) );
		vec3 F = F_Schlick( f0, f90, dotVH );
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
		return F * ( V * D );
	}
#endif
vec3 BRDF_GGX( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, const in PhysicalMaterial material ) {
	vec3 f0 = material.specularColor;
	float f90 = material.specularF90;
	float roughness = material.roughness;
	float alpha = pow2( roughness );
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float dotVH = saturate( dot( viewDir, halfDir ) );
	vec3 F = F_Schlick( f0, f90, dotVH );
	#ifdef USE_IRIDESCENCE
		F = mix( F, material.iridescenceFresnel, material.iridescence );
	#endif
	#ifdef USE_ANISOTROPY
		float dotTL = dot( material.anisotropyT, lightDir );
		float dotTV = dot( material.anisotropyT, viewDir );
		float dotTH = dot( material.anisotropyT, halfDir );
		float dotBL = dot( material.anisotropyB, lightDir );
		float dotBV = dot( material.anisotropyB, viewDir );
		float dotBH = dot( material.anisotropyB, halfDir );
		float V = V_GGX_SmithCorrelated_Anisotropic( material.alphaT, alpha, dotTV, dotBV, dotTL, dotBL, dotNV, dotNL );
		float D = D_GGX_Anisotropic( material.alphaT, alpha, dotNH, dotTH, dotBH );
	#else
		float V = V_GGX_SmithCorrelated( alpha, dotNL, dotNV );
		float D = D_GGX( alpha, dotNH );
	#endif
	return F * ( V * D );
}
vec2 LTC_Uv( const in vec3 N, const in vec3 V, const in float roughness ) {
	const float LUT_SIZE = 64.0;
	const float LUT_SCALE = ( LUT_SIZE - 1.0 ) / LUT_SIZE;
	const float LUT_BIAS = 0.5 / LUT_SIZE;
	float dotNV = saturate( dot( N, V ) );
	vec2 uv = vec2( roughness, sqrt( 1.0 - dotNV ) );
	uv = uv * LUT_SCALE + LUT_BIAS;
	return uv;
}
float LTC_ClippedSphereFormFactor( const in vec3 f ) {
	float l = length( f );
	return max( ( l * l + f.z ) / ( l + 1.0 ), 0.0 );
}
vec3 LTC_EdgeVectorFormFactor( const in vec3 v1, const in vec3 v2 ) {
	float x = dot( v1, v2 );
	float y = abs( x );
	float a = 0.8543985 + ( 0.4965155 + 0.0145206 * y ) * y;
	float b = 3.4175940 + ( 4.1616724 + y ) * y;
	float v = a / b;
	float theta_sintheta = ( x > 0.0 ) ? v : 0.5 * inversesqrt( max( 1.0 - x * x, 1e-7 ) ) - v;
	return cross( v1, v2 ) * theta_sintheta;
}
vec3 LTC_Evaluate( const in vec3 N, const in vec3 V, const in vec3 P, const in mat3 mInv, const in vec3 rectCoords[ 4 ] ) {
	vec3 v1 = rectCoords[ 1 ] - rectCoords[ 0 ];
	vec3 v2 = rectCoords[ 3 ] - rectCoords[ 0 ];
	vec3 lightNormal = cross( v1, v2 );
	if( dot( lightNormal, P - rectCoords[ 0 ] ) < 0.0 ) return vec3( 0.0 );
	vec3 T1, T2;
	T1 = normalize( V - N * dot( V, N ) );
	T2 = - cross( N, T1 );
	mat3 mat = mInv * transposeMat3( mat3( T1, T2, N ) );
	vec3 coords[ 4 ];
	coords[ 0 ] = mat * ( rectCoords[ 0 ] - P );
	coords[ 1 ] = mat * ( rectCoords[ 1 ] - P );
	coords[ 2 ] = mat * ( rectCoords[ 2 ] - P );
	coords[ 3 ] = mat * ( rectCoords[ 3 ] - P );
	coords[ 0 ] = normalize( coords[ 0 ] );
	coords[ 1 ] = normalize( coords[ 1 ] );
	coords[ 2 ] = normalize( coords[ 2 ] );
	coords[ 3 ] = normalize( coords[ 3 ] );
	vec3 vectorFormFactor = vec3( 0.0 );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 0 ], coords[ 1 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 1 ], coords[ 2 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 2 ], coords[ 3 ] );
	vectorFormFactor += LTC_EdgeVectorFormFactor( coords[ 3 ], coords[ 0 ] );
	float result = LTC_ClippedSphereFormFactor( vectorFormFactor );
	return vec3( result );
}
#if defined( USE_SHEEN )
float D_Charlie( float roughness, float dotNH ) {
	float alpha = pow2( roughness );
	float invAlpha = 1.0 / alpha;
	float cos2h = dotNH * dotNH;
	float sin2h = max( 1.0 - cos2h, 0.0078125 );
	return ( 2.0 + invAlpha ) * pow( sin2h, invAlpha * 0.5 ) / ( 2.0 * PI );
}
float V_Neubelt( float dotNV, float dotNL ) {
	return saturate( 1.0 / ( 4.0 * ( dotNL + dotNV - dotNL * dotNV ) ) );
}
vec3 BRDF_Sheen( const in vec3 lightDir, const in vec3 viewDir, const in vec3 normal, vec3 sheenColor, const in float sheenRoughness ) {
	vec3 halfDir = normalize( lightDir + viewDir );
	float dotNL = saturate( dot( normal, lightDir ) );
	float dotNV = saturate( dot( normal, viewDir ) );
	float dotNH = saturate( dot( normal, halfDir ) );
	float D = D_Charlie( sheenRoughness, dotNH );
	float V = V_Neubelt( dotNV, dotNL );
	return sheenColor * ( D * V );
}
#endif
float IBLSheenBRDF( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	float r2 = roughness * roughness;
	float a = roughness < 0.25 ? -339.2 * r2 + 161.4 * roughness - 25.9 : -8.48 * r2 + 14.3 * roughness - 9.95;
	float b = roughness < 0.25 ? 44.0 * r2 - 23.7 * roughness + 3.26 : 1.97 * r2 - 3.27 * roughness + 0.72;
	float DG = exp( a * dotNV + b ) + ( roughness < 0.25 ? 0.0 : 0.1 * ( roughness - 0.25 ) );
	return saturate( DG * RECIPROCAL_PI );
}
vec2 DFGApprox( const in vec3 normal, const in vec3 viewDir, const in float roughness ) {
	float dotNV = saturate( dot( normal, viewDir ) );
	const vec4 c0 = vec4( - 1, - 0.0275, - 0.572, 0.022 );
	const vec4 c1 = vec4( 1, 0.0425, 1.04, - 0.04 );
	vec4 r = roughness * c0 + c1;
	float a004 = min( r.x * r.x, exp2( - 9.28 * dotNV ) ) * r.x + r.y;
	vec2 fab = vec2( - 1.04, 1.04 ) * a004 + r.zw;
	return fab;
}
vec3 EnvironmentBRDF( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness ) {
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	return specularColor * fab.x + specularF90 * fab.y;
}
#ifdef USE_IRIDESCENCE
void computeMultiscatteringIridescence( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float iridescence, const in vec3 iridescenceF0, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#else
void computeMultiscattering( const in vec3 normal, const in vec3 viewDir, const in vec3 specularColor, const in float specularF90, const in float roughness, inout vec3 singleScatter, inout vec3 multiScatter ) {
#endif
	vec2 fab = DFGApprox( normal, viewDir, roughness );
	#ifdef USE_IRIDESCENCE
		vec3 Fr = mix( specularColor, iridescenceF0, iridescence );
	#else
		vec3 Fr = specularColor;
	#endif
	vec3 FssEss = Fr * fab.x + specularF90 * fab.y;
	float Ess = fab.x + fab.y;
	float Ems = 1.0 - Ess;
	vec3 Favg = Fr + ( 1.0 - Fr ) * 0.047619;	vec3 Fms = FssEss * Favg / ( 1.0 - Ems * Favg );
	singleScatter += FssEss;
	multiScatter += Fms * Ems;
}
#if NUM_RECT_AREA_LIGHTS > 0
	void RE_Direct_RectArea_Physical( const in RectAreaLight rectAreaLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
		vec3 normal = geometryNormal;
		vec3 viewDir = geometryViewDir;
		vec3 position = geometryPosition;
		vec3 lightPos = rectAreaLight.position;
		vec3 halfWidth = rectAreaLight.halfWidth;
		vec3 halfHeight = rectAreaLight.halfHeight;
		vec3 lightColor = rectAreaLight.color;
		float roughness = material.roughness;
		vec3 rectCoords[ 4 ];
		rectCoords[ 0 ] = lightPos + halfWidth - halfHeight;		rectCoords[ 1 ] = lightPos - halfWidth - halfHeight;
		rectCoords[ 2 ] = lightPos - halfWidth + halfHeight;
		rectCoords[ 3 ] = lightPos + halfWidth + halfHeight;
		vec2 uv = LTC_Uv( normal, viewDir, roughness );
		vec4 t1 = texture2D( ltc_1, uv );
		vec4 t2 = texture2D( ltc_2, uv );
		mat3 mInv = mat3(
			vec3( t1.x, 0, t1.y ),
			vec3(    0, 1,    0 ),
			vec3( t1.z, 0, t1.w )
		);
		vec3 fresnel = ( material.specularColor * t2.x + ( vec3( 1.0 ) - material.specularColor ) * t2.y );
		reflectedLight.directSpecular += lightColor * fresnel * LTC_Evaluate( normal, viewDir, position, mInv, rectCoords );
		reflectedLight.directDiffuse += lightColor * material.diffuseColor * LTC_Evaluate( normal, viewDir, position, mat3( 1.0 ), rectCoords );
	}
#endif
void RE_Direct_Physical( const in IncidentLight directLight, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	float dotNL = saturate( dot( geometryNormal, directLight.direction ) );
	vec3 irradiance = dotNL * directLight.color;
	#ifdef USE_CLEARCOAT
		float dotNLcc = saturate( dot( geometryClearcoatNormal, directLight.direction ) );
		vec3 ccIrradiance = dotNLcc * directLight.color;
		clearcoatSpecularDirect += ccIrradiance * BRDF_GGX_Clearcoat( directLight.direction, geometryViewDir, geometryClearcoatNormal, material );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularDirect += irradiance * BRDF_Sheen( directLight.direction, geometryViewDir, geometryNormal, material.sheenColor, material.sheenRoughness );
	#endif
	reflectedLight.directSpecular += irradiance * BRDF_GGX( directLight.direction, geometryViewDir, geometryNormal, material );
	reflectedLight.directDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectDiffuse_Physical( const in vec3 irradiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight ) {
	reflectedLight.indirectDiffuse += irradiance * BRDF_Lambert( material.diffuseColor );
}
void RE_IndirectSpecular_Physical( const in vec3 radiance, const in vec3 irradiance, const in vec3 clearcoatRadiance, const in vec3 geometryPosition, const in vec3 geometryNormal, const in vec3 geometryViewDir, const in vec3 geometryClearcoatNormal, const in PhysicalMaterial material, inout ReflectedLight reflectedLight) {
	#ifdef USE_CLEARCOAT
		clearcoatSpecularIndirect += clearcoatRadiance * EnvironmentBRDF( geometryClearcoatNormal, geometryViewDir, material.clearcoatF0, material.clearcoatF90, material.clearcoatRoughness );
	#endif
	#ifdef USE_SHEEN
		sheenSpecularIndirect += irradiance * material.sheenColor * IBLSheenBRDF( geometryNormal, geometryViewDir, material.sheenRoughness );
	#endif
	vec3 singleScattering = vec3( 0.0 );
	vec3 multiScattering = vec3( 0.0 );
	vec3 cosineWeightedIrradiance = irradiance * RECIPROCAL_PI;
	#ifdef USE_IRIDESCENCE
		computeMultiscatteringIridescence( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.iridescence, material.iridescenceFresnel, material.roughness, singleScattering, multiScattering );
	#else
		computeMultiscattering( geometryNormal, geometryViewDir, material.specularColor, material.specularF90, material.roughness, singleScattering, multiScattering );
	#endif
	vec3 totalScattering = singleScattering + multiScattering;
	vec3 diffuse = material.diffuseColor * ( 1.0 - max( max( totalScattering.r, totalScattering.g ), totalScattering.b ) );
	reflectedLight.indirectSpecular += radiance * singleScattering;
	reflectedLight.indirectSpecular += multiScattering * cosineWeightedIrradiance;
	reflectedLight.indirectDiffuse += diffuse * cosineWeightedIrradiance;
}
#define RE_Direct				RE_Direct_Physical
#define RE_Direct_RectArea		RE_Direct_RectArea_Physical
#define RE_IndirectDiffuse		RE_IndirectDiffuse_Physical
#define RE_IndirectSpecular		RE_IndirectSpecular_Physical
float computeSpecularOcclusion( const in float dotNV, const in float ambientOcclusion, const in float roughness ) {
	return saturate( pow( dotNV + ambientOcclusion, exp2( - 16.0 * roughness - 1.0 ) ) - 1.0 + ambientOcclusion );
}`,qm=`
vec3 geometryPosition = - vViewPosition;
vec3 geometryNormal = normal;
vec3 geometryViewDir = ( isOrthographic ) ? vec3( 0, 0, 1 ) : normalize( vViewPosition );
vec3 geometryClearcoatNormal = vec3( 0.0 );
#ifdef USE_CLEARCOAT
	geometryClearcoatNormal = clearcoatNormal;
#endif
#ifdef USE_IRIDESCENCE
	float dotNVi = saturate( dot( normal, geometryViewDir ) );
	if ( material.iridescenceThickness == 0.0 ) {
		material.iridescence = 0.0;
	} else {
		material.iridescence = saturate( material.iridescence );
	}
	if ( material.iridescence > 0.0 ) {
		material.iridescenceFresnel = evalIridescence( 1.0, material.iridescenceIOR, dotNVi, material.iridescenceThickness, material.specularColor );
		material.iridescenceF0 = Schlick_to_F0( material.iridescenceFresnel, 1.0, dotNVi );
	}
#endif
IncidentLight directLight;
#if ( NUM_POINT_LIGHTS > 0 ) && defined( RE_Direct )
	PointLight pointLight;
	#if defined( USE_SHADOWMAP ) && NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHTS; i ++ ) {
		pointLight = pointLights[ i ];
		getPointLightInfo( pointLight, geometryPosition, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_POINT_LIGHT_SHADOWS )
		pointLightShadow = pointLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getPointShadow( pointShadowMap[ i ], pointLightShadow.shadowMapSize, pointLightShadow.shadowIntensity, pointLightShadow.shadowBias, pointLightShadow.shadowRadius, vPointShadowCoord[ i ], pointLightShadow.shadowCameraNear, pointLightShadow.shadowCameraFar ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_SPOT_LIGHTS > 0 ) && defined( RE_Direct )
	SpotLight spotLight;
	vec4 spotColor;
	vec3 spotLightCoord;
	bool inSpotLightMap;
	#if defined( USE_SHADOWMAP ) && NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHTS; i ++ ) {
		spotLight = spotLights[ i ];
		getSpotLightInfo( spotLight, geometryPosition, directLight );
		#if ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#define SPOT_LIGHT_MAP_INDEX UNROLLED_LOOP_INDEX
		#elif ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		#define SPOT_LIGHT_MAP_INDEX NUM_SPOT_LIGHT_MAPS
		#else
		#define SPOT_LIGHT_MAP_INDEX ( UNROLLED_LOOP_INDEX - NUM_SPOT_LIGHT_SHADOWS + NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS )
		#endif
		#if ( SPOT_LIGHT_MAP_INDEX < NUM_SPOT_LIGHT_MAPS )
			spotLightCoord = vSpotLightCoord[ i ].xyz / vSpotLightCoord[ i ].w;
			inSpotLightMap = all( lessThan( abs( spotLightCoord * 2. - 1. ), vec3( 1.0 ) ) );
			spotColor = texture2D( spotLightMap[ SPOT_LIGHT_MAP_INDEX ], spotLightCoord.xy );
			directLight.color = inSpotLightMap ? directLight.color * spotColor.rgb : directLight.color;
		#endif
		#undef SPOT_LIGHT_MAP_INDEX
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
		spotLightShadow = spotLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( spotShadowMap[ i ], spotLightShadow.shadowMapSize, spotLightShadow.shadowIntensity, spotLightShadow.shadowBias, spotLightShadow.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )
	DirectionalLight directionalLight;
	#if defined( USE_SHADOWMAP ) && NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLightShadow;
	#endif
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHTS; i ++ ) {
		directionalLight = directionalLights[ i ];
		getDirectionalLightInfo( directionalLight, directLight );
		#if defined( USE_SHADOWMAP ) && ( UNROLLED_LOOP_INDEX < NUM_DIR_LIGHT_SHADOWS )
		directionalLightShadow = directionalLightShadows[ i ];
		directLight.color *= ( directLight.visible && receiveShadow ) ? getShadow( directionalShadowMap[ i ], directionalLightShadow.shadowMapSize, directionalLightShadow.shadowIntensity, directionalLightShadow.shadowBias, directionalLightShadow.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
		#endif
		RE_Direct( directLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if ( NUM_RECT_AREA_LIGHTS > 0 ) && defined( RE_Direct_RectArea )
	RectAreaLight rectAreaLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_RECT_AREA_LIGHTS; i ++ ) {
		rectAreaLight = rectAreaLights[ i ];
		RE_Direct_RectArea( rectAreaLight, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
	}
	#pragma unroll_loop_end
#endif
#if defined( RE_IndirectDiffuse )
	vec3 iblIrradiance = vec3( 0.0 );
	vec3 irradiance = getAmbientLightIrradiance( ambientLightColor );
	#if defined( USE_LIGHT_PROBES )
		irradiance += getLightProbeIrradiance( lightProbe, geometryNormal );
	#endif
	#if ( NUM_HEMI_LIGHTS > 0 )
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_HEMI_LIGHTS; i ++ ) {
			irradiance += getHemisphereLightIrradiance( hemisphereLights[ i ], geometryNormal );
		}
		#pragma unroll_loop_end
	#endif
#endif
#if defined( RE_IndirectSpecular )
	vec3 radiance = vec3( 0.0 );
	vec3 clearcoatRadiance = vec3( 0.0 );
#endif`,Ym=`#if defined( RE_IndirectDiffuse )
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		vec3 lightMapIrradiance = lightMapTexel.rgb * lightMapIntensity;
		irradiance += lightMapIrradiance;
	#endif
	#if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
		iblIrradiance += getIBLIrradiance( geometryNormal );
	#endif
#endif
#if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
	#ifdef USE_ANISOTROPY
		radiance += getIBLAnisotropyRadiance( geometryViewDir, geometryNormal, material.roughness, material.anisotropyB, material.anisotropy );
	#else
		radiance += getIBLRadiance( geometryViewDir, geometryNormal, material.roughness );
	#endif
	#ifdef USE_CLEARCOAT
		clearcoatRadiance += getIBLRadiance( geometryViewDir, geometryClearcoatNormal, material.clearcoatRoughness );
	#endif
#endif`,$m=`#if defined( RE_IndirectDiffuse )
	RE_IndirectDiffuse( irradiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif
#if defined( RE_IndirectSpecular )
	RE_IndirectSpecular( radiance, iblIrradiance, clearcoatRadiance, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
#endif`,Zm=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	gl_FragDepth = vIsPerspective == 0.0 ? gl_FragCoord.z : log2( vFragDepth ) * logDepthBufFC * 0.5;
#endif`,Jm=`#if defined( USE_LOGARITHMIC_DEPTH_BUFFER )
	uniform float logDepthBufFC;
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,Km=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	varying float vFragDepth;
	varying float vIsPerspective;
#endif`,jm=`#ifdef USE_LOGARITHMIC_DEPTH_BUFFER
	vFragDepth = 1.0 + gl_Position.w;
	vIsPerspective = float( isPerspectiveMatrix( projectionMatrix ) );
#endif`,Qm=`#ifdef USE_MAP
	vec4 sampledDiffuseColor = texture2D( map, vMapUv );
	#ifdef DECODE_VIDEO_TEXTURE
		sampledDiffuseColor = sRGBTransferEOTF( sampledDiffuseColor );
	#endif
	diffuseColor *= sampledDiffuseColor;
#endif`,eg=`#ifdef USE_MAP
	uniform sampler2D map;
#endif`,tg=`#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
	#if defined( USE_POINTS_UV )
		vec2 uv = vUv;
	#else
		vec2 uv = ( uvTransform * vec3( gl_PointCoord.x, 1.0 - gl_PointCoord.y, 1 ) ).xy;
	#endif
#endif
#ifdef USE_MAP
	diffuseColor *= texture2D( map, uv );
#endif
#ifdef USE_ALPHAMAP
	diffuseColor.a *= texture2D( alphaMap, uv ).g;
#endif`,ng=`#if defined( USE_POINTS_UV )
	varying vec2 vUv;
#else
	#if defined( USE_MAP ) || defined( USE_ALPHAMAP )
		uniform mat3 uvTransform;
	#endif
#endif
#ifdef USE_MAP
	uniform sampler2D map;
#endif
#ifdef USE_ALPHAMAP
	uniform sampler2D alphaMap;
#endif`,ig=`float metalnessFactor = metalness;
#ifdef USE_METALNESSMAP
	vec4 texelMetalness = texture2D( metalnessMap, vMetalnessMapUv );
	metalnessFactor *= texelMetalness.b;
#endif`,sg=`#ifdef USE_METALNESSMAP
	uniform sampler2D metalnessMap;
#endif`,rg=`#ifdef USE_INSTANCING_MORPH
	float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	float morphTargetBaseInfluence = texelFetch( morphTexture, ivec2( 0, gl_InstanceID ), 0 ).r;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		morphTargetInfluences[i] =  texelFetch( morphTexture, ivec2( i + 1, gl_InstanceID ), 0 ).r;
	}
#endif`,ag=`#if defined( USE_MORPHCOLORS )
	vColor *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		#if defined( USE_COLOR_ALPHA )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ) * morphTargetInfluences[ i ];
		#elif defined( USE_COLOR )
			if ( morphTargetInfluences[ i ] != 0.0 ) vColor += getMorph( gl_VertexID, i, 2 ).rgb * morphTargetInfluences[ i ];
		#endif
	}
#endif`,og=`#ifdef USE_MORPHNORMALS
	objectNormal *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) objectNormal += getMorph( gl_VertexID, i, 1 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,lg=`#ifdef USE_MORPHTARGETS
	#ifndef USE_INSTANCING_MORPH
		uniform float morphTargetBaseInfluence;
		uniform float morphTargetInfluences[ MORPHTARGETS_COUNT ];
	#endif
	uniform sampler2DArray morphTargetsTexture;
	uniform ivec2 morphTargetsTextureSize;
	vec4 getMorph( const in int vertexIndex, const in int morphTargetIndex, const in int offset ) {
		int texelIndex = vertexIndex * MORPHTARGETS_TEXTURE_STRIDE + offset;
		int y = texelIndex / morphTargetsTextureSize.x;
		int x = texelIndex - y * morphTargetsTextureSize.x;
		ivec3 morphUV = ivec3( x, y, morphTargetIndex );
		return texelFetch( morphTargetsTexture, morphUV, 0 );
	}
#endif`,cg=`#ifdef USE_MORPHTARGETS
	transformed *= morphTargetBaseInfluence;
	for ( int i = 0; i < MORPHTARGETS_COUNT; i ++ ) {
		if ( morphTargetInfluences[ i ] != 0.0 ) transformed += getMorph( gl_VertexID, i, 0 ).xyz * morphTargetInfluences[ i ];
	}
#endif`,hg=`float faceDirection = gl_FrontFacing ? 1.0 : - 1.0;
#ifdef FLAT_SHADED
	vec3 fdx = dFdx( vViewPosition );
	vec3 fdy = dFdy( vViewPosition );
	vec3 normal = normalize( cross( fdx, fdy ) );
#else
	vec3 normal = normalize( vNormal );
	#ifdef DOUBLE_SIDED
		normal *= faceDirection;
	#endif
#endif
#if defined( USE_NORMALMAP_TANGENTSPACE ) || defined( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY )
	#ifdef USE_TANGENT
		mat3 tbn = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn = getTangentFrame( - vViewPosition, normal,
		#if defined( USE_NORMALMAP )
			vNormalMapUv
		#elif defined( USE_CLEARCOAT_NORMALMAP )
			vClearcoatNormalMapUv
		#else
			vUv
		#endif
		);
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn[0] *= faceDirection;
		tbn[1] *= faceDirection;
	#endif
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	#ifdef USE_TANGENT
		mat3 tbn2 = mat3( normalize( vTangent ), normalize( vBitangent ), normal );
	#else
		mat3 tbn2 = getTangentFrame( - vViewPosition, normal, vClearcoatNormalMapUv );
	#endif
	#if defined( DOUBLE_SIDED ) && ! defined( FLAT_SHADED )
		tbn2[0] *= faceDirection;
		tbn2[1] *= faceDirection;
	#endif
#endif
vec3 nonPerturbedNormal = normal;`,ug=`#ifdef USE_NORMALMAP_OBJECTSPACE
	normal = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	#ifdef FLIP_SIDED
		normal = - normal;
	#endif
	#ifdef DOUBLE_SIDED
		normal = normal * faceDirection;
	#endif
	normal = normalize( normalMatrix * normal );
#elif defined( USE_NORMALMAP_TANGENTSPACE )
	vec3 mapN = texture2D( normalMap, vNormalMapUv ).xyz * 2.0 - 1.0;
	mapN.xy *= normalScale;
	normal = normalize( tbn * mapN );
#elif defined( USE_BUMPMAP )
	normal = perturbNormalArb( - vViewPosition, normal, dHdxy_fwd(), faceDirection );
#endif`,dg=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,fg=`#ifndef FLAT_SHADED
	varying vec3 vNormal;
	#ifdef USE_TANGENT
		varying vec3 vTangent;
		varying vec3 vBitangent;
	#endif
#endif`,pg=`#ifndef FLAT_SHADED
	vNormal = normalize( transformedNormal );
	#ifdef USE_TANGENT
		vTangent = normalize( transformedTangent );
		vBitangent = normalize( cross( vNormal, vTangent ) * tangent.w );
	#endif
#endif`,mg=`#ifdef USE_NORMALMAP
	uniform sampler2D normalMap;
	uniform vec2 normalScale;
#endif
#ifdef USE_NORMALMAP_OBJECTSPACE
	uniform mat3 normalMatrix;
#endif
#if ! defined ( USE_TANGENT ) && ( defined ( USE_NORMALMAP_TANGENTSPACE ) || defined ( USE_CLEARCOAT_NORMALMAP ) || defined( USE_ANISOTROPY ) )
	mat3 getTangentFrame( vec3 eye_pos, vec3 surf_norm, vec2 uv ) {
		vec3 q0 = dFdx( eye_pos.xyz );
		vec3 q1 = dFdy( eye_pos.xyz );
		vec2 st0 = dFdx( uv.st );
		vec2 st1 = dFdy( uv.st );
		vec3 N = surf_norm;
		vec3 q1perp = cross( q1, N );
		vec3 q0perp = cross( N, q0 );
		vec3 T = q1perp * st0.x + q0perp * st1.x;
		vec3 B = q1perp * st0.y + q0perp * st1.y;
		float det = max( dot( T, T ), dot( B, B ) );
		float scale = ( det == 0.0 ) ? 0.0 : inversesqrt( det );
		return mat3( T * scale, B * scale, N );
	}
#endif`,gg=`#ifdef USE_CLEARCOAT
	vec3 clearcoatNormal = nonPerturbedNormal;
#endif`,_g=`#ifdef USE_CLEARCOAT_NORMALMAP
	vec3 clearcoatMapN = texture2D( clearcoatNormalMap, vClearcoatNormalMapUv ).xyz * 2.0 - 1.0;
	clearcoatMapN.xy *= clearcoatNormalScale;
	clearcoatNormal = normalize( tbn2 * clearcoatMapN );
#endif`,xg=`#ifdef USE_CLEARCOATMAP
	uniform sampler2D clearcoatMap;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform sampler2D clearcoatNormalMap;
	uniform vec2 clearcoatNormalScale;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform sampler2D clearcoatRoughnessMap;
#endif`,vg=`#ifdef USE_IRIDESCENCEMAP
	uniform sampler2D iridescenceMap;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform sampler2D iridescenceThicknessMap;
#endif`,yg=`#ifdef OPAQUE
diffuseColor.a = 1.0;
#endif
#ifdef USE_TRANSMISSION
diffuseColor.a *= material.transmissionAlpha;
#endif
gl_FragColor = vec4( outgoingLight, diffuseColor.a );`,wg=`vec3 packNormalToRGB( const in vec3 normal ) {
	return normalize( normal ) * 0.5 + 0.5;
}
vec3 unpackRGBToNormal( const in vec3 rgb ) {
	return 2.0 * rgb.xyz - 1.0;
}
const float PackUpscale = 256. / 255.;const float UnpackDownscale = 255. / 256.;const float ShiftRight8 = 1. / 256.;
const float Inv255 = 1. / 255.;
const vec4 PackFactors = vec4( 1.0, 256.0, 256.0 * 256.0, 256.0 * 256.0 * 256.0 );
const vec2 UnpackFactors2 = vec2( UnpackDownscale, 1.0 / PackFactors.g );
const vec3 UnpackFactors3 = vec3( UnpackDownscale / PackFactors.rg, 1.0 / PackFactors.b );
const vec4 UnpackFactors4 = vec4( UnpackDownscale / PackFactors.rgb, 1.0 / PackFactors.a );
vec4 packDepthToRGBA( const in float v ) {
	if( v <= 0.0 )
		return vec4( 0., 0., 0., 0. );
	if( v >= 1.0 )
		return vec4( 1., 1., 1., 1. );
	float vuf;
	float af = modf( v * PackFactors.a, vuf );
	float bf = modf( vuf * ShiftRight8, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec4( vuf * Inv255, gf * PackUpscale, bf * PackUpscale, af );
}
vec3 packDepthToRGB( const in float v ) {
	if( v <= 0.0 )
		return vec3( 0., 0., 0. );
	if( v >= 1.0 )
		return vec3( 1., 1., 1. );
	float vuf;
	float bf = modf( v * PackFactors.b, vuf );
	float gf = modf( vuf * ShiftRight8, vuf );
	return vec3( vuf * Inv255, gf * PackUpscale, bf );
}
vec2 packDepthToRG( const in float v ) {
	if( v <= 0.0 )
		return vec2( 0., 0. );
	if( v >= 1.0 )
		return vec2( 1., 1. );
	float vuf;
	float gf = modf( v * 256., vuf );
	return vec2( vuf * Inv255, gf );
}
float unpackRGBAToDepth( const in vec4 v ) {
	return dot( v, UnpackFactors4 );
}
float unpackRGBToDepth( const in vec3 v ) {
	return dot( v, UnpackFactors3 );
}
float unpackRGToDepth( const in vec2 v ) {
	return v.r * UnpackFactors2.r + v.g * UnpackFactors2.g;
}
vec4 pack2HalfToRGBA( const in vec2 v ) {
	vec4 r = vec4( v.x, fract( v.x * 255.0 ), v.y, fract( v.y * 255.0 ) );
	return vec4( r.x - r.y / 255.0, r.y, r.z - r.w / 255.0, r.w );
}
vec2 unpackRGBATo2Half( const in vec4 v ) {
	return vec2( v.x + ( v.y / 255.0 ), v.z + ( v.w / 255.0 ) );
}
float viewZToOrthographicDepth( const in float viewZ, const in float near, const in float far ) {
	return ( viewZ + near ) / ( near - far );
}
float orthographicDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return depth * ( near - far ) - near;
}
float viewZToPerspectiveDepth( const in float viewZ, const in float near, const in float far ) {
	return ( ( near + viewZ ) * far ) / ( ( far - near ) * viewZ );
}
float perspectiveDepthToViewZ( const in float depth, const in float near, const in float far ) {
	return ( near * far ) / ( ( far - near ) * depth - far );
}`,bg=`#ifdef PREMULTIPLIED_ALPHA
	gl_FragColor.rgb *= gl_FragColor.a;
#endif`,Mg=`vec4 mvPosition = vec4( transformed, 1.0 );
#ifdef USE_BATCHING
	mvPosition = batchingMatrix * mvPosition;
#endif
#ifdef USE_INSTANCING
	mvPosition = instanceMatrix * mvPosition;
#endif
mvPosition = modelViewMatrix * mvPosition;
gl_Position = projectionMatrix * mvPosition;`,Sg=`#ifdef DITHERING
	gl_FragColor.rgb = dithering( gl_FragColor.rgb );
#endif`,Tg=`#ifdef DITHERING
	vec3 dithering( vec3 color ) {
		float grid_position = rand( gl_FragCoord.xy );
		vec3 dither_shift_RGB = vec3( 0.25 / 255.0, -0.25 / 255.0, 0.25 / 255.0 );
		dither_shift_RGB = mix( 2.0 * dither_shift_RGB, -2.0 * dither_shift_RGB, grid_position );
		return color + dither_shift_RGB;
	}
#endif`,Eg=`float roughnessFactor = roughness;
#ifdef USE_ROUGHNESSMAP
	vec4 texelRoughness = texture2D( roughnessMap, vRoughnessMapUv );
	roughnessFactor *= texelRoughness.g;
#endif`,Ag=`#ifdef USE_ROUGHNESSMAP
	uniform sampler2D roughnessMap;
#endif`,Cg=`#if NUM_SPOT_LIGHT_COORDS > 0
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#if NUM_SPOT_LIGHT_MAPS > 0
	uniform sampler2D spotLightMap[ NUM_SPOT_LIGHT_MAPS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform sampler2D directionalShadowMap[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		uniform sampler2D spotShadowMap[ NUM_SPOT_LIGHT_SHADOWS ];
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform sampler2D pointShadowMap[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
	float texture2DCompare( sampler2D depths, vec2 uv, float compare ) {
		float depth = unpackRGBAToDepth( texture2D( depths, uv ) );
		#ifdef USE_REVERSED_DEPTH_BUFFER
			return step( depth, compare );
		#else
			return step( compare, depth );
		#endif
	}
	vec2 texture2DDistribution( sampler2D shadow, vec2 uv ) {
		return unpackRGBATo2Half( texture2D( shadow, uv ) );
	}
	float VSMShadow( sampler2D shadow, vec2 uv, float compare ) {
		float occlusion = 1.0;
		vec2 distribution = texture2DDistribution( shadow, uv );
		#ifdef USE_REVERSED_DEPTH_BUFFER
			float hard_shadow = step( distribution.x, compare );
		#else
			float hard_shadow = step( compare, distribution.x );
		#endif
		if ( hard_shadow != 1.0 ) {
			float distance = compare - distribution.x;
			float variance = max( 0.00000, distribution.y * distribution.y );
			float softness_probability = variance / (variance + distance * distance );			softness_probability = clamp( ( softness_probability - 0.3 ) / ( 0.95 - 0.3 ), 0.0, 1.0 );			occlusion = clamp( max( hard_shadow, softness_probability ), 0.0, 1.0 );
		}
		return occlusion;
	}
	float getShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord ) {
		float shadow = 1.0;
		shadowCoord.xyz /= shadowCoord.w;
		shadowCoord.z += shadowBias;
		bool inFrustum = shadowCoord.x >= 0.0 && shadowCoord.x <= 1.0 && shadowCoord.y >= 0.0 && shadowCoord.y <= 1.0;
		bool frustumTest = inFrustum && shadowCoord.z <= 1.0;
		if ( frustumTest ) {
		#if defined( SHADOWMAP_TYPE_PCF )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx0 = - texelSize.x * shadowRadius;
			float dy0 = - texelSize.y * shadowRadius;
			float dx1 = + texelSize.x * shadowRadius;
			float dy1 = + texelSize.y * shadowRadius;
			float dx2 = dx0 / 2.0;
			float dy2 = dy0 / 2.0;
			float dx3 = dx1 / 2.0;
			float dy3 = dy1 / 2.0;
			shadow = (
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy2 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx2, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx3, dy3 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( 0.0, dy1 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, shadowCoord.xy + vec2( dx1, dy1 ), shadowCoord.z )
			) * ( 1.0 / 17.0 );
		#elif defined( SHADOWMAP_TYPE_PCF_SOFT )
			vec2 texelSize = vec2( 1.0 ) / shadowMapSize;
			float dx = texelSize.x;
			float dy = texelSize.y;
			vec2 uv = shadowCoord.xy;
			vec2 f = fract( uv * shadowMapSize + 0.5 );
			uv -= f * texelSize;
			shadow = (
				texture2DCompare( shadowMap, uv, shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( dx, 0.0 ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + vec2( 0.0, dy ), shadowCoord.z ) +
				texture2DCompare( shadowMap, uv + texelSize, shadowCoord.z ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, 0.0 ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 0.0 ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( -dx, dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, dy ), shadowCoord.z ),
					 f.x ) +
				mix( texture2DCompare( shadowMap, uv + vec2( 0.0, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( 0.0, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( texture2DCompare( shadowMap, uv + vec2( dx, -dy ), shadowCoord.z ),
					 texture2DCompare( shadowMap, uv + vec2( dx, 2.0 * dy ), shadowCoord.z ),
					 f.y ) +
				mix( mix( texture2DCompare( shadowMap, uv + vec2( -dx, -dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, -dy ), shadowCoord.z ),
						  f.x ),
					 mix( texture2DCompare( shadowMap, uv + vec2( -dx, 2.0 * dy ), shadowCoord.z ),
						  texture2DCompare( shadowMap, uv + vec2( 2.0 * dx, 2.0 * dy ), shadowCoord.z ),
						  f.x ),
					 f.y )
			) * ( 1.0 / 9.0 );
		#elif defined( SHADOWMAP_TYPE_VSM )
			shadow = VSMShadow( shadowMap, shadowCoord.xy, shadowCoord.z );
		#else
			shadow = texture2DCompare( shadowMap, shadowCoord.xy, shadowCoord.z );
		#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
	vec2 cubeToUV( vec3 v, float texelSizeY ) {
		vec3 absV = abs( v );
		float scaleToCube = 1.0 / max( absV.x, max( absV.y, absV.z ) );
		absV *= scaleToCube;
		v *= scaleToCube * ( 1.0 - 2.0 * texelSizeY );
		vec2 planar = v.xy;
		float almostATexel = 1.5 * texelSizeY;
		float almostOne = 1.0 - almostATexel;
		if ( absV.z >= almostOne ) {
			if ( v.z > 0.0 )
				planar.x = 4.0 - v.x;
		} else if ( absV.x >= almostOne ) {
			float signX = sign( v.x );
			planar.x = v.z * signX + 2.0 * signX;
		} else if ( absV.y >= almostOne ) {
			float signY = sign( v.y );
			planar.x = v.x + 2.0 * signY + 2.0;
			planar.y = v.z * signY - 2.0;
		}
		return vec2( 0.125, 0.25 ) * planar + vec2( 0.375, 0.75 );
	}
	float getPointShadow( sampler2D shadowMap, vec2 shadowMapSize, float shadowIntensity, float shadowBias, float shadowRadius, vec4 shadowCoord, float shadowCameraNear, float shadowCameraFar ) {
		float shadow = 1.0;
		vec3 lightToPosition = shadowCoord.xyz;
		
		float lightToPositionLength = length( lightToPosition );
		if ( lightToPositionLength - shadowCameraFar <= 0.0 && lightToPositionLength - shadowCameraNear >= 0.0 ) {
			float dp = ( lightToPositionLength - shadowCameraNear ) / ( shadowCameraFar - shadowCameraNear );			dp += shadowBias;
			vec3 bd3D = normalize( lightToPosition );
			vec2 texelSize = vec2( 1.0 ) / ( shadowMapSize * vec2( 4.0, 2.0 ) );
			#if defined( SHADOWMAP_TYPE_PCF ) || defined( SHADOWMAP_TYPE_PCF_SOFT ) || defined( SHADOWMAP_TYPE_VSM )
				vec2 offset = vec2( - 1, 1 ) * shadowRadius * texelSize.y;
				shadow = (
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yyx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxy, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.xxx, texelSize.y ), dp ) +
					texture2DCompare( shadowMap, cubeToUV( bd3D + offset.yxx, texelSize.y ), dp )
				) * ( 1.0 / 9.0 );
			#else
				shadow = texture2DCompare( shadowMap, cubeToUV( bd3D, texelSize.y ), dp );
			#endif
		}
		return mix( 1.0, shadow, shadowIntensity );
	}
#endif`,Rg=`#if NUM_SPOT_LIGHT_COORDS > 0
	uniform mat4 spotLightMatrix[ NUM_SPOT_LIGHT_COORDS ];
	varying vec4 vSpotLightCoord[ NUM_SPOT_LIGHT_COORDS ];
#endif
#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
		uniform mat4 directionalShadowMatrix[ NUM_DIR_LIGHT_SHADOWS ];
		varying vec4 vDirectionalShadowCoord[ NUM_DIR_LIGHT_SHADOWS ];
		struct DirectionalLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform DirectionalLightShadow directionalLightShadows[ NUM_DIR_LIGHT_SHADOWS ];
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
		struct SpotLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
		};
		uniform SpotLightShadow spotLightShadows[ NUM_SPOT_LIGHT_SHADOWS ];
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		uniform mat4 pointShadowMatrix[ NUM_POINT_LIGHT_SHADOWS ];
		varying vec4 vPointShadowCoord[ NUM_POINT_LIGHT_SHADOWS ];
		struct PointLightShadow {
			float shadowIntensity;
			float shadowBias;
			float shadowNormalBias;
			float shadowRadius;
			vec2 shadowMapSize;
			float shadowCameraNear;
			float shadowCameraFar;
		};
		uniform PointLightShadow pointLightShadows[ NUM_POINT_LIGHT_SHADOWS ];
	#endif
#endif`,Pg=`#if ( defined( USE_SHADOWMAP ) && ( NUM_DIR_LIGHT_SHADOWS > 0 || NUM_POINT_LIGHT_SHADOWS > 0 ) ) || ( NUM_SPOT_LIGHT_COORDS > 0 )
	vec3 shadowWorldNormal = inverseTransformDirection( transformedNormal, viewMatrix );
	vec4 shadowWorldPosition;
#endif
#if defined( USE_SHADOWMAP )
	#if NUM_DIR_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * directionalLightShadows[ i ].shadowNormalBias, 0 );
			vDirectionalShadowCoord[ i ] = directionalShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
		#pragma unroll_loop_start
		for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
			shadowWorldPosition = worldPosition + vec4( shadowWorldNormal * pointLightShadows[ i ].shadowNormalBias, 0 );
			vPointShadowCoord[ i ] = pointShadowMatrix[ i ] * shadowWorldPosition;
		}
		#pragma unroll_loop_end
	#endif
#endif
#if NUM_SPOT_LIGHT_COORDS > 0
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_COORDS; i ++ ) {
		shadowWorldPosition = worldPosition;
		#if ( defined( USE_SHADOWMAP ) && UNROLLED_LOOP_INDEX < NUM_SPOT_LIGHT_SHADOWS )
			shadowWorldPosition.xyz += shadowWorldNormal * spotLightShadows[ i ].shadowNormalBias;
		#endif
		vSpotLightCoord[ i ] = spotLightMatrix[ i ] * shadowWorldPosition;
	}
	#pragma unroll_loop_end
#endif`,Ig=`float getShadowMask() {
	float shadow = 1.0;
	#ifdef USE_SHADOWMAP
	#if NUM_DIR_LIGHT_SHADOWS > 0
	DirectionalLightShadow directionalLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_DIR_LIGHT_SHADOWS; i ++ ) {
		directionalLight = directionalLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( directionalShadowMap[ i ], directionalLight.shadowMapSize, directionalLight.shadowIntensity, directionalLight.shadowBias, directionalLight.shadowRadius, vDirectionalShadowCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_SPOT_LIGHT_SHADOWS > 0
	SpotLightShadow spotLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_SPOT_LIGHT_SHADOWS; i ++ ) {
		spotLight = spotLightShadows[ i ];
		shadow *= receiveShadow ? getShadow( spotShadowMap[ i ], spotLight.shadowMapSize, spotLight.shadowIntensity, spotLight.shadowBias, spotLight.shadowRadius, vSpotLightCoord[ i ] ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#if NUM_POINT_LIGHT_SHADOWS > 0
	PointLightShadow pointLight;
	#pragma unroll_loop_start
	for ( int i = 0; i < NUM_POINT_LIGHT_SHADOWS; i ++ ) {
		pointLight = pointLightShadows[ i ];
		shadow *= receiveShadow ? getPointShadow( pointShadowMap[ i ], pointLight.shadowMapSize, pointLight.shadowIntensity, pointLight.shadowBias, pointLight.shadowRadius, vPointShadowCoord[ i ], pointLight.shadowCameraNear, pointLight.shadowCameraFar ) : 1.0;
	}
	#pragma unroll_loop_end
	#endif
	#endif
	return shadow;
}`,Ng=`#ifdef USE_SKINNING
	mat4 boneMatX = getBoneMatrix( skinIndex.x );
	mat4 boneMatY = getBoneMatrix( skinIndex.y );
	mat4 boneMatZ = getBoneMatrix( skinIndex.z );
	mat4 boneMatW = getBoneMatrix( skinIndex.w );
#endif`,Dg=`#ifdef USE_SKINNING
	uniform mat4 bindMatrix;
	uniform mat4 bindMatrixInverse;
	uniform highp sampler2D boneTexture;
	mat4 getBoneMatrix( const in float i ) {
		int size = textureSize( boneTexture, 0 ).x;
		int j = int( i ) * 4;
		int x = j % size;
		int y = j / size;
		vec4 v1 = texelFetch( boneTexture, ivec2( x, y ), 0 );
		vec4 v2 = texelFetch( boneTexture, ivec2( x + 1, y ), 0 );
		vec4 v3 = texelFetch( boneTexture, ivec2( x + 2, y ), 0 );
		vec4 v4 = texelFetch( boneTexture, ivec2( x + 3, y ), 0 );
		return mat4( v1, v2, v3, v4 );
	}
#endif`,Lg=`#ifdef USE_SKINNING
	vec4 skinVertex = bindMatrix * vec4( transformed, 1.0 );
	vec4 skinned = vec4( 0.0 );
	skinned += boneMatX * skinVertex * skinWeight.x;
	skinned += boneMatY * skinVertex * skinWeight.y;
	skinned += boneMatZ * skinVertex * skinWeight.z;
	skinned += boneMatW * skinVertex * skinWeight.w;
	transformed = ( bindMatrixInverse * skinned ).xyz;
#endif`,Ug=`#ifdef USE_SKINNING
	mat4 skinMatrix = mat4( 0.0 );
	skinMatrix += skinWeight.x * boneMatX;
	skinMatrix += skinWeight.y * boneMatY;
	skinMatrix += skinWeight.z * boneMatZ;
	skinMatrix += skinWeight.w * boneMatW;
	skinMatrix = bindMatrixInverse * skinMatrix * bindMatrix;
	objectNormal = vec4( skinMatrix * vec4( objectNormal, 0.0 ) ).xyz;
	#ifdef USE_TANGENT
		objectTangent = vec4( skinMatrix * vec4( objectTangent, 0.0 ) ).xyz;
	#endif
#endif`,Fg=`float specularStrength;
#ifdef USE_SPECULARMAP
	vec4 texelSpecular = texture2D( specularMap, vSpecularMapUv );
	specularStrength = texelSpecular.r;
#else
	specularStrength = 1.0;
#endif`,Og=`#ifdef USE_SPECULARMAP
	uniform sampler2D specularMap;
#endif`,kg=`#if defined( TONE_MAPPING )
	gl_FragColor.rgb = toneMapping( gl_FragColor.rgb );
#endif`,Bg=`#ifndef saturate
#define saturate( a ) clamp( a, 0.0, 1.0 )
#endif
uniform float toneMappingExposure;
vec3 LinearToneMapping( vec3 color ) {
	return saturate( toneMappingExposure * color );
}
vec3 ReinhardToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	return saturate( color / ( vec3( 1.0 ) + color ) );
}
vec3 CineonToneMapping( vec3 color ) {
	color *= toneMappingExposure;
	color = max( vec3( 0.0 ), color - 0.004 );
	return pow( ( color * ( 6.2 * color + 0.5 ) ) / ( color * ( 6.2 * color + 1.7 ) + 0.06 ), vec3( 2.2 ) );
}
vec3 RRTAndODTFit( vec3 v ) {
	vec3 a = v * ( v + 0.0245786 ) - 0.000090537;
	vec3 b = v * ( 0.983729 * v + 0.4329510 ) + 0.238081;
	return a / b;
}
vec3 ACESFilmicToneMapping( vec3 color ) {
	const mat3 ACESInputMat = mat3(
		vec3( 0.59719, 0.07600, 0.02840 ),		vec3( 0.35458, 0.90834, 0.13383 ),
		vec3( 0.04823, 0.01566, 0.83777 )
	);
	const mat3 ACESOutputMat = mat3(
		vec3(  1.60475, -0.10208, -0.00327 ),		vec3( -0.53108,  1.10813, -0.07276 ),
		vec3( -0.07367, -0.00605,  1.07602 )
	);
	color *= toneMappingExposure / 0.6;
	color = ACESInputMat * color;
	color = RRTAndODTFit( color );
	color = ACESOutputMat * color;
	return saturate( color );
}
const mat3 LINEAR_REC2020_TO_LINEAR_SRGB = mat3(
	vec3( 1.6605, - 0.1246, - 0.0182 ),
	vec3( - 0.5876, 1.1329, - 0.1006 ),
	vec3( - 0.0728, - 0.0083, 1.1187 )
);
const mat3 LINEAR_SRGB_TO_LINEAR_REC2020 = mat3(
	vec3( 0.6274, 0.0691, 0.0164 ),
	vec3( 0.3293, 0.9195, 0.0880 ),
	vec3( 0.0433, 0.0113, 0.8956 )
);
vec3 agxDefaultContrastApprox( vec3 x ) {
	vec3 x2 = x * x;
	vec3 x4 = x2 * x2;
	return + 15.5 * x4 * x2
		- 40.14 * x4 * x
		+ 31.96 * x4
		- 6.868 * x2 * x
		+ 0.4298 * x2
		+ 0.1191 * x
		- 0.00232;
}
vec3 AgXToneMapping( vec3 color ) {
	const mat3 AgXInsetMatrix = mat3(
		vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ),
		vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ),
		vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 )
	);
	const mat3 AgXOutsetMatrix = mat3(
		vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ),
		vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ),
		vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 )
	);
	const float AgxMinEv = - 12.47393;	const float AgxMaxEv = 4.026069;
	color *= toneMappingExposure;
	color = LINEAR_SRGB_TO_LINEAR_REC2020 * color;
	color = AgXInsetMatrix * color;
	color = max( color, 1e-10 );	color = log2( color );
	color = ( color - AgxMinEv ) / ( AgxMaxEv - AgxMinEv );
	color = clamp( color, 0.0, 1.0 );
	color = agxDefaultContrastApprox( color );
	color = AgXOutsetMatrix * color;
	color = pow( max( vec3( 0.0 ), color ), vec3( 2.2 ) );
	color = LINEAR_REC2020_TO_LINEAR_SRGB * color;
	color = clamp( color, 0.0, 1.0 );
	return color;
}
vec3 NeutralToneMapping( vec3 color ) {
	const float StartCompression = 0.8 - 0.04;
	const float Desaturation = 0.15;
	color *= toneMappingExposure;
	float x = min( color.r, min( color.g, color.b ) );
	float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
	color -= offset;
	float peak = max( color.r, max( color.g, color.b ) );
	if ( peak < StartCompression ) return color;
	float d = 1. - StartCompression;
	float newPeak = 1. - d * d / ( peak + d - StartCompression );
	color *= newPeak / peak;
	float g = 1. - 1. / ( Desaturation * ( peak - newPeak ) + 1. );
	return mix( color, vec3( newPeak ), g );
}
vec3 CustomToneMapping( vec3 color ) { return color; }`,zg=`#ifdef USE_TRANSMISSION
	material.transmission = transmission;
	material.transmissionAlpha = 1.0;
	material.thickness = thickness;
	material.attenuationDistance = attenuationDistance;
	material.attenuationColor = attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		material.transmission *= texture2D( transmissionMap, vTransmissionMapUv ).r;
	#endif
	#ifdef USE_THICKNESSMAP
		material.thickness *= texture2D( thicknessMap, vThicknessMapUv ).g;
	#endif
	vec3 pos = vWorldPosition;
	vec3 v = normalize( cameraPosition - pos );
	vec3 n = inverseTransformDirection( normal, viewMatrix );
	vec4 transmitted = getIBLVolumeRefraction(
		n, v, material.roughness, material.diffuseColor, material.specularColor, material.specularF90,
		pos, modelMatrix, viewMatrix, projectionMatrix, material.dispersion, material.ior, material.thickness,
		material.attenuationColor, material.attenuationDistance );
	material.transmissionAlpha = mix( material.transmissionAlpha, transmitted.a, material.transmission );
	totalDiffuse = mix( totalDiffuse, transmitted.rgb, material.transmission );
#endif`,Vg=`#ifdef USE_TRANSMISSION
	uniform float transmission;
	uniform float thickness;
	uniform float attenuationDistance;
	uniform vec3 attenuationColor;
	#ifdef USE_TRANSMISSIONMAP
		uniform sampler2D transmissionMap;
	#endif
	#ifdef USE_THICKNESSMAP
		uniform sampler2D thicknessMap;
	#endif
	uniform vec2 transmissionSamplerSize;
	uniform sampler2D transmissionSamplerMap;
	uniform mat4 modelMatrix;
	uniform mat4 projectionMatrix;
	varying vec3 vWorldPosition;
	float w0( float a ) {
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - a + 3.0 ) - 3.0 ) + 1.0 );
	}
	float w1( float a ) {
		return ( 1.0 / 6.0 ) * ( a *  a * ( 3.0 * a - 6.0 ) + 4.0 );
	}
	float w2( float a ){
		return ( 1.0 / 6.0 ) * ( a * ( a * ( - 3.0 * a + 3.0 ) + 3.0 ) + 1.0 );
	}
	float w3( float a ) {
		return ( 1.0 / 6.0 ) * ( a * a * a );
	}
	float g0( float a ) {
		return w0( a ) + w1( a );
	}
	float g1( float a ) {
		return w2( a ) + w3( a );
	}
	float h0( float a ) {
		return - 1.0 + w1( a ) / ( w0( a ) + w1( a ) );
	}
	float h1( float a ) {
		return 1.0 + w3( a ) / ( w2( a ) + w3( a ) );
	}
	vec4 bicubic( sampler2D tex, vec2 uv, vec4 texelSize, float lod ) {
		uv = uv * texelSize.zw + 0.5;
		vec2 iuv = floor( uv );
		vec2 fuv = fract( uv );
		float g0x = g0( fuv.x );
		float g1x = g1( fuv.x );
		float h0x = h0( fuv.x );
		float h1x = h1( fuv.x );
		float h0y = h0( fuv.y );
		float h1y = h1( fuv.y );
		vec2 p0 = ( vec2( iuv.x + h0x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p1 = ( vec2( iuv.x + h1x, iuv.y + h0y ) - 0.5 ) * texelSize.xy;
		vec2 p2 = ( vec2( iuv.x + h0x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		vec2 p3 = ( vec2( iuv.x + h1x, iuv.y + h1y ) - 0.5 ) * texelSize.xy;
		return g0( fuv.y ) * ( g0x * textureLod( tex, p0, lod ) + g1x * textureLod( tex, p1, lod ) ) +
			g1( fuv.y ) * ( g0x * textureLod( tex, p2, lod ) + g1x * textureLod( tex, p3, lod ) );
	}
	vec4 textureBicubic( sampler2D sampler, vec2 uv, float lod ) {
		vec2 fLodSize = vec2( textureSize( sampler, int( lod ) ) );
		vec2 cLodSize = vec2( textureSize( sampler, int( lod + 1.0 ) ) );
		vec2 fLodSizeInv = 1.0 / fLodSize;
		vec2 cLodSizeInv = 1.0 / cLodSize;
		vec4 fSample = bicubic( sampler, uv, vec4( fLodSizeInv, fLodSize ), floor( lod ) );
		vec4 cSample = bicubic( sampler, uv, vec4( cLodSizeInv, cLodSize ), ceil( lod ) );
		return mix( fSample, cSample, fract( lod ) );
	}
	vec3 getVolumeTransmissionRay( const in vec3 n, const in vec3 v, const in float thickness, const in float ior, const in mat4 modelMatrix ) {
		vec3 refractionVector = refract( - v, normalize( n ), 1.0 / ior );
		vec3 modelScale;
		modelScale.x = length( vec3( modelMatrix[ 0 ].xyz ) );
		modelScale.y = length( vec3( modelMatrix[ 1 ].xyz ) );
		modelScale.z = length( vec3( modelMatrix[ 2 ].xyz ) );
		return normalize( refractionVector ) * thickness * modelScale;
	}
	float applyIorToRoughness( const in float roughness, const in float ior ) {
		return roughness * clamp( ior * 2.0 - 2.0, 0.0, 1.0 );
	}
	vec4 getTransmissionSample( const in vec2 fragCoord, const in float roughness, const in float ior ) {
		float lod = log2( transmissionSamplerSize.x ) * applyIorToRoughness( roughness, ior );
		return textureBicubic( transmissionSamplerMap, fragCoord.xy, lod );
	}
	vec3 volumeAttenuation( const in float transmissionDistance, const in vec3 attenuationColor, const in float attenuationDistance ) {
		if ( isinf( attenuationDistance ) ) {
			return vec3( 1.0 );
		} else {
			vec3 attenuationCoefficient = -log( attenuationColor ) / attenuationDistance;
			vec3 transmittance = exp( - attenuationCoefficient * transmissionDistance );			return transmittance;
		}
	}
	vec4 getIBLVolumeRefraction( const in vec3 n, const in vec3 v, const in float roughness, const in vec3 diffuseColor,
		const in vec3 specularColor, const in float specularF90, const in vec3 position, const in mat4 modelMatrix,
		const in mat4 viewMatrix, const in mat4 projMatrix, const in float dispersion, const in float ior, const in float thickness,
		const in vec3 attenuationColor, const in float attenuationDistance ) {
		vec4 transmittedLight;
		vec3 transmittance;
		#ifdef USE_DISPERSION
			float halfSpread = ( ior - 1.0 ) * 0.025 * dispersion;
			vec3 iors = vec3( ior - halfSpread, ior, ior + halfSpread );
			for ( int i = 0; i < 3; i ++ ) {
				vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, iors[ i ], modelMatrix );
				vec3 refractedRayExit = position + transmissionRay;
				vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
				vec2 refractionCoords = ndcPos.xy / ndcPos.w;
				refractionCoords += 1.0;
				refractionCoords /= 2.0;
				vec4 transmissionSample = getTransmissionSample( refractionCoords, roughness, iors[ i ] );
				transmittedLight[ i ] = transmissionSample[ i ];
				transmittedLight.a += transmissionSample.a;
				transmittance[ i ] = diffuseColor[ i ] * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance )[ i ];
			}
			transmittedLight.a /= 3.0;
		#else
			vec3 transmissionRay = getVolumeTransmissionRay( n, v, thickness, ior, modelMatrix );
			vec3 refractedRayExit = position + transmissionRay;
			vec4 ndcPos = projMatrix * viewMatrix * vec4( refractedRayExit, 1.0 );
			vec2 refractionCoords = ndcPos.xy / ndcPos.w;
			refractionCoords += 1.0;
			refractionCoords /= 2.0;
			transmittedLight = getTransmissionSample( refractionCoords, roughness, ior );
			transmittance = diffuseColor * volumeAttenuation( length( transmissionRay ), attenuationColor, attenuationDistance );
		#endif
		vec3 attenuatedColor = transmittance * transmittedLight.rgb;
		vec3 F = EnvironmentBRDF( n, v, specularColor, specularF90, roughness );
		float transmittanceFactor = ( transmittance.r + transmittance.g + transmittance.b ) / 3.0;
		return vec4( ( 1.0 - F ) * attenuatedColor, 1.0 - ( 1.0 - transmittedLight.a ) * transmittanceFactor );
	}
#endif`,Hg=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_SPECULARMAP
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,Gg=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	varying vec2 vUv;
#endif
#ifdef USE_MAP
	uniform mat3 mapTransform;
	varying vec2 vMapUv;
#endif
#ifdef USE_ALPHAMAP
	uniform mat3 alphaMapTransform;
	varying vec2 vAlphaMapUv;
#endif
#ifdef USE_LIGHTMAP
	uniform mat3 lightMapTransform;
	varying vec2 vLightMapUv;
#endif
#ifdef USE_AOMAP
	uniform mat3 aoMapTransform;
	varying vec2 vAoMapUv;
#endif
#ifdef USE_BUMPMAP
	uniform mat3 bumpMapTransform;
	varying vec2 vBumpMapUv;
#endif
#ifdef USE_NORMALMAP
	uniform mat3 normalMapTransform;
	varying vec2 vNormalMapUv;
#endif
#ifdef USE_DISPLACEMENTMAP
	uniform mat3 displacementMapTransform;
	varying vec2 vDisplacementMapUv;
#endif
#ifdef USE_EMISSIVEMAP
	uniform mat3 emissiveMapTransform;
	varying vec2 vEmissiveMapUv;
#endif
#ifdef USE_METALNESSMAP
	uniform mat3 metalnessMapTransform;
	varying vec2 vMetalnessMapUv;
#endif
#ifdef USE_ROUGHNESSMAP
	uniform mat3 roughnessMapTransform;
	varying vec2 vRoughnessMapUv;
#endif
#ifdef USE_ANISOTROPYMAP
	uniform mat3 anisotropyMapTransform;
	varying vec2 vAnisotropyMapUv;
#endif
#ifdef USE_CLEARCOATMAP
	uniform mat3 clearcoatMapTransform;
	varying vec2 vClearcoatMapUv;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	uniform mat3 clearcoatNormalMapTransform;
	varying vec2 vClearcoatNormalMapUv;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	uniform mat3 clearcoatRoughnessMapTransform;
	varying vec2 vClearcoatRoughnessMapUv;
#endif
#ifdef USE_SHEEN_COLORMAP
	uniform mat3 sheenColorMapTransform;
	varying vec2 vSheenColorMapUv;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	uniform mat3 sheenRoughnessMapTransform;
	varying vec2 vSheenRoughnessMapUv;
#endif
#ifdef USE_IRIDESCENCEMAP
	uniform mat3 iridescenceMapTransform;
	varying vec2 vIridescenceMapUv;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	uniform mat3 iridescenceThicknessMapTransform;
	varying vec2 vIridescenceThicknessMapUv;
#endif
#ifdef USE_SPECULARMAP
	uniform mat3 specularMapTransform;
	varying vec2 vSpecularMapUv;
#endif
#ifdef USE_SPECULAR_COLORMAP
	uniform mat3 specularColorMapTransform;
	varying vec2 vSpecularColorMapUv;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	uniform mat3 specularIntensityMapTransform;
	varying vec2 vSpecularIntensityMapUv;
#endif
#ifdef USE_TRANSMISSIONMAP
	uniform mat3 transmissionMapTransform;
	varying vec2 vTransmissionMapUv;
#endif
#ifdef USE_THICKNESSMAP
	uniform mat3 thicknessMapTransform;
	varying vec2 vThicknessMapUv;
#endif`,Wg=`#if defined( USE_UV ) || defined( USE_ANISOTROPY )
	vUv = vec3( uv, 1 ).xy;
#endif
#ifdef USE_MAP
	vMapUv = ( mapTransform * vec3( MAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ALPHAMAP
	vAlphaMapUv = ( alphaMapTransform * vec3( ALPHAMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_LIGHTMAP
	vLightMapUv = ( lightMapTransform * vec3( LIGHTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_AOMAP
	vAoMapUv = ( aoMapTransform * vec3( AOMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_BUMPMAP
	vBumpMapUv = ( bumpMapTransform * vec3( BUMPMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_NORMALMAP
	vNormalMapUv = ( normalMapTransform * vec3( NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_DISPLACEMENTMAP
	vDisplacementMapUv = ( displacementMapTransform * vec3( DISPLACEMENTMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_EMISSIVEMAP
	vEmissiveMapUv = ( emissiveMapTransform * vec3( EMISSIVEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_METALNESSMAP
	vMetalnessMapUv = ( metalnessMapTransform * vec3( METALNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ROUGHNESSMAP
	vRoughnessMapUv = ( roughnessMapTransform * vec3( ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_ANISOTROPYMAP
	vAnisotropyMapUv = ( anisotropyMapTransform * vec3( ANISOTROPYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOATMAP
	vClearcoatMapUv = ( clearcoatMapTransform * vec3( CLEARCOATMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_NORMALMAP
	vClearcoatNormalMapUv = ( clearcoatNormalMapTransform * vec3( CLEARCOAT_NORMALMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_CLEARCOAT_ROUGHNESSMAP
	vClearcoatRoughnessMapUv = ( clearcoatRoughnessMapTransform * vec3( CLEARCOAT_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCEMAP
	vIridescenceMapUv = ( iridescenceMapTransform * vec3( IRIDESCENCEMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_IRIDESCENCE_THICKNESSMAP
	vIridescenceThicknessMapUv = ( iridescenceThicknessMapTransform * vec3( IRIDESCENCE_THICKNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_COLORMAP
	vSheenColorMapUv = ( sheenColorMapTransform * vec3( SHEEN_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SHEEN_ROUGHNESSMAP
	vSheenRoughnessMapUv = ( sheenRoughnessMapTransform * vec3( SHEEN_ROUGHNESSMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULARMAP
	vSpecularMapUv = ( specularMapTransform * vec3( SPECULARMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_COLORMAP
	vSpecularColorMapUv = ( specularColorMapTransform * vec3( SPECULAR_COLORMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_SPECULAR_INTENSITYMAP
	vSpecularIntensityMapUv = ( specularIntensityMapTransform * vec3( SPECULAR_INTENSITYMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_TRANSMISSIONMAP
	vTransmissionMapUv = ( transmissionMapTransform * vec3( TRANSMISSIONMAP_UV, 1 ) ).xy;
#endif
#ifdef USE_THICKNESSMAP
	vThicknessMapUv = ( thicknessMapTransform * vec3( THICKNESSMAP_UV, 1 ) ).xy;
#endif`,Xg=`#if defined( USE_ENVMAP ) || defined( DISTANCE ) || defined ( USE_SHADOWMAP ) || defined ( USE_TRANSMISSION ) || NUM_SPOT_LIGHT_COORDS > 0
	vec4 worldPosition = vec4( transformed, 1.0 );
	#ifdef USE_BATCHING
		worldPosition = batchingMatrix * worldPosition;
	#endif
	#ifdef USE_INSTANCING
		worldPosition = instanceMatrix * worldPosition;
	#endif
	worldPosition = modelMatrix * worldPosition;
#endif`,qg=`varying vec2 vUv;
uniform mat3 uvTransform;
void main() {
	vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	gl_Position = vec4( position.xy, 1.0, 1.0 );
}`,Yg=`uniform sampler2D t2D;
uniform float backgroundIntensity;
varying vec2 vUv;
void main() {
	vec4 texColor = texture2D( t2D, vUv );
	#ifdef DECODE_VIDEO_TEXTURE
		texColor = vec4( mix( pow( texColor.rgb * 0.9478672986 + vec3( 0.0521327014 ), vec3( 2.4 ) ), texColor.rgb * 0.0773993808, vec3( lessThanEqual( texColor.rgb, vec3( 0.04045 ) ) ) ), texColor.w );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,$g=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,Zg=`#ifdef ENVMAP_TYPE_CUBE
	uniform samplerCube envMap;
#elif defined( ENVMAP_TYPE_CUBE_UV )
	uniform sampler2D envMap;
#endif
uniform float flipEnvMap;
uniform float backgroundBlurriness;
uniform float backgroundIntensity;
uniform mat3 backgroundRotation;
varying vec3 vWorldDirection;
#include <cube_uv_reflection_fragment>
void main() {
	#ifdef ENVMAP_TYPE_CUBE
		vec4 texColor = textureCube( envMap, backgroundRotation * vec3( flipEnvMap * vWorldDirection.x, vWorldDirection.yz ) );
	#elif defined( ENVMAP_TYPE_CUBE_UV )
		vec4 texColor = textureCubeUV( envMap, backgroundRotation * vWorldDirection, backgroundBlurriness );
	#else
		vec4 texColor = vec4( 0.0, 0.0, 0.0, 1.0 );
	#endif
	texColor.rgb *= backgroundIntensity;
	gl_FragColor = texColor;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,Jg=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
	gl_Position.z = gl_Position.w;
}`,Kg=`uniform samplerCube tCube;
uniform float tFlip;
uniform float opacity;
varying vec3 vWorldDirection;
void main() {
	vec4 texColor = textureCube( tCube, vec3( tFlip * vWorldDirection.x, vWorldDirection.yz ) );
	gl_FragColor = texColor;
	gl_FragColor.a *= opacity;
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,jg=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
varying vec2 vHighPrecisionZW;
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vHighPrecisionZW = gl_Position.zw;
}`,Qg=`#if DEPTH_PACKING == 3200
	uniform float opacity;
#endif
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
varying vec2 vHighPrecisionZW;
void main() {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#if DEPTH_PACKING == 3200
		diffuseColor.a = opacity;
	#endif
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <logdepthbuf_fragment>
	#ifdef USE_REVERSED_DEPTH_BUFFER
		float fragCoordZ = vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ];
	#else
		float fragCoordZ = 0.5 * vHighPrecisionZW[ 0 ] / vHighPrecisionZW[ 1 ] + 0.5;
	#endif
	#if DEPTH_PACKING == 3200
		gl_FragColor = vec4( vec3( 1.0 - fragCoordZ ), opacity );
	#elif DEPTH_PACKING == 3201
		gl_FragColor = packDepthToRGBA( fragCoordZ );
	#elif DEPTH_PACKING == 3202
		gl_FragColor = vec4( packDepthToRGB( fragCoordZ ), 1.0 );
	#elif DEPTH_PACKING == 3203
		gl_FragColor = vec4( packDepthToRG( fragCoordZ ), 0.0, 1.0 );
	#endif
}`,e_=`#define DISTANCE
varying vec3 vWorldPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <skinbase_vertex>
	#include <morphinstance_vertex>
	#ifdef USE_DISPLACEMENTMAP
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <worldpos_vertex>
	#include <clipping_planes_vertex>
	vWorldPosition = worldPosition.xyz;
}`,t_=`#define DISTANCE
uniform vec3 referencePosition;
uniform float nearDistance;
uniform float farDistance;
varying vec3 vWorldPosition;
#include <common>
#include <packing>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <clipping_planes_pars_fragment>
void main () {
	vec4 diffuseColor = vec4( 1.0 );
	#include <clipping_planes_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	float dist = length( vWorldPosition - referencePosition );
	dist = ( dist - nearDistance ) / ( farDistance - nearDistance );
	dist = saturate( dist );
	gl_FragColor = packDepthToRGBA( dist );
}`,n_=`varying vec3 vWorldDirection;
#include <common>
void main() {
	vWorldDirection = transformDirection( position, modelMatrix );
	#include <begin_vertex>
	#include <project_vertex>
}`,i_=`uniform sampler2D tEquirect;
varying vec3 vWorldDirection;
#include <common>
void main() {
	vec3 direction = normalize( vWorldDirection );
	vec2 sampleUV = equirectUv( direction );
	gl_FragColor = texture2D( tEquirect, sampleUV );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
}`,s_=`uniform float scale;
attribute float lineDistance;
varying float vLineDistance;
#include <common>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	vLineDistance = scale * lineDistance;
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,r_=`uniform vec3 diffuse;
uniform float opacity;
uniform float dashSize;
uniform float totalSize;
varying float vLineDistance;
#include <common>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	if ( mod( vLineDistance, totalSize ) > dashSize ) {
		discard;
	}
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,a_=`#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#if defined ( USE_ENVMAP ) || defined ( USE_SKINNING )
		#include <beginnormal_vertex>
		#include <morphnormal_vertex>
		#include <skinbase_vertex>
		#include <skinnormal_vertex>
		#include <defaultnormal_vertex>
	#endif
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <fog_vertex>
}`,o_=`uniform vec3 diffuse;
uniform float opacity;
#ifndef FLAT_SHADED
	varying vec3 vNormal;
#endif
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	#ifdef USE_LIGHTMAP
		vec4 lightMapTexel = texture2D( lightMap, vLightMapUv );
		reflectedLight.indirectDiffuse += lightMapTexel.rgb * lightMapIntensity * RECIPROCAL_PI;
	#else
		reflectedLight.indirectDiffuse += vec3( 1.0 );
	#endif
	#include <aomap_fragment>
	reflectedLight.indirectDiffuse *= diffuseColor.rgb;
	vec3 outgoingLight = reflectedLight.indirectDiffuse;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,l_=`#define LAMBERT
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,c_=`#define LAMBERT
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_lambert_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_lambert_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,h_=`#define MATCAP
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <color_pars_vertex>
#include <displacementmap_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
	vViewPosition = - mvPosition.xyz;
}`,u_=`#define MATCAP
uniform vec3 diffuse;
uniform float opacity;
uniform sampler2D matcap;
varying vec3 vViewPosition;
#include <common>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	vec3 viewDir = normalize( vViewPosition );
	vec3 x = normalize( vec3( viewDir.z, 0.0, - viewDir.x ) );
	vec3 y = cross( viewDir, x );
	vec2 uv = vec2( dot( x, normal ), dot( y, normal ) ) * 0.495 + 0.5;
	#ifdef USE_MATCAP
		vec4 matcapColor = texture2D( matcap, uv );
	#else
		vec4 matcapColor = vec4( vec3( mix( 0.2, 0.8, uv.y ) ), 1.0 );
	#endif
	vec3 outgoingLight = diffuseColor.rgb * matcapColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,d_=`#define NORMAL
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	vViewPosition = - mvPosition.xyz;
#endif
}`,f_=`#define NORMAL
uniform float opacity;
#if defined( FLAT_SHADED ) || defined( USE_BUMPMAP ) || defined( USE_NORMALMAP_TANGENTSPACE )
	varying vec3 vViewPosition;
#endif
#include <packing>
#include <uv_pars_fragment>
#include <normal_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( 0.0, 0.0, 0.0, opacity );
	#include <clipping_planes_fragment>
	#include <logdepthbuf_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	gl_FragColor = vec4( packNormalToRGB( normal ), diffuseColor.a );
	#ifdef OPAQUE
		gl_FragColor.a = 1.0;
	#endif
}`,p_=`#define PHONG
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <envmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <envmap_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,m_=`#define PHONG
uniform vec3 diffuse;
uniform vec3 emissive;
uniform vec3 specular;
uniform float shininess;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_phong_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <specularmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <specularmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_phong_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + reflectedLight.directSpecular + reflectedLight.indirectSpecular + totalEmissiveRadiance;
	#include <envmap_fragment>
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,g_=`#define STANDARD
varying vec3 vViewPosition;
#ifdef USE_TRANSMISSION
	varying vec3 vWorldPosition;
#endif
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
#ifdef USE_TRANSMISSION
	vWorldPosition = worldPosition.xyz;
#endif
}`,__=`#define STANDARD
#ifdef PHYSICAL
	#define IOR
	#define USE_SPECULAR
#endif
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float roughness;
uniform float metalness;
uniform float opacity;
#ifdef IOR
	uniform float ior;
#endif
#ifdef USE_SPECULAR
	uniform float specularIntensity;
	uniform vec3 specularColor;
	#ifdef USE_SPECULAR_COLORMAP
		uniform sampler2D specularColorMap;
	#endif
	#ifdef USE_SPECULAR_INTENSITYMAP
		uniform sampler2D specularIntensityMap;
	#endif
#endif
#ifdef USE_CLEARCOAT
	uniform float clearcoat;
	uniform float clearcoatRoughness;
#endif
#ifdef USE_DISPERSION
	uniform float dispersion;
#endif
#ifdef USE_IRIDESCENCE
	uniform float iridescence;
	uniform float iridescenceIOR;
	uniform float iridescenceThicknessMinimum;
	uniform float iridescenceThicknessMaximum;
#endif
#ifdef USE_SHEEN
	uniform vec3 sheenColor;
	uniform float sheenRoughness;
	#ifdef USE_SHEEN_COLORMAP
		uniform sampler2D sheenColorMap;
	#endif
	#ifdef USE_SHEEN_ROUGHNESSMAP
		uniform sampler2D sheenRoughnessMap;
	#endif
#endif
#ifdef USE_ANISOTROPY
	uniform vec2 anisotropyVector;
	#ifdef USE_ANISOTROPYMAP
		uniform sampler2D anisotropyMap;
	#endif
#endif
varying vec3 vViewPosition;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <iridescence_fragment>
#include <cube_uv_reflection_fragment>
#include <envmap_common_pars_fragment>
#include <envmap_physical_pars_fragment>
#include <fog_pars_fragment>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_physical_pars_fragment>
#include <transmission_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <clearcoat_pars_fragment>
#include <iridescence_pars_fragment>
#include <roughnessmap_pars_fragment>
#include <metalnessmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <roughnessmap_fragment>
	#include <metalnessmap_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <clearcoat_normal_fragment_begin>
	#include <clearcoat_normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_physical_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 totalDiffuse = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse;
	vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
	#include <transmission_fragment>
	vec3 outgoingLight = totalDiffuse + totalSpecular + totalEmissiveRadiance;
	#ifdef USE_SHEEN
		float sheenEnergyComp = 1.0 - 0.157 * max3( material.sheenColor );
		outgoingLight = outgoingLight * sheenEnergyComp + sheenSpecularDirect + sheenSpecularIndirect;
	#endif
	#ifdef USE_CLEARCOAT
		float dotNVcc = saturate( dot( geometryClearcoatNormal, geometryViewDir ) );
		vec3 Fcc = F_Schlick( material.clearcoatF0, material.clearcoatF90, dotNVcc );
		outgoingLight = outgoingLight * ( 1.0 - material.clearcoat * Fcc ) + ( clearcoatSpecularDirect + clearcoatSpecularIndirect ) * material.clearcoat;
	#endif
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,x_=`#define TOON
varying vec3 vViewPosition;
#include <common>
#include <batching_pars_vertex>
#include <uv_pars_vertex>
#include <displacementmap_pars_vertex>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <normal_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <shadowmap_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <normal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <displacementmap_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	vViewPosition = - mvPosition.xyz;
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,v_=`#define TOON
uniform vec3 diffuse;
uniform vec3 emissive;
uniform float opacity;
#include <common>
#include <packing>
#include <dithering_pars_fragment>
#include <color_pars_fragment>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <aomap_pars_fragment>
#include <lightmap_pars_fragment>
#include <emissivemap_pars_fragment>
#include <gradientmap_pars_fragment>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <normal_pars_fragment>
#include <lights_toon_pars_fragment>
#include <shadowmap_pars_fragment>
#include <bumpmap_pars_fragment>
#include <normalmap_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	ReflectedLight reflectedLight = ReflectedLight( vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ), vec3( 0.0 ) );
	vec3 totalEmissiveRadiance = emissive;
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <color_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	#include <normal_fragment_begin>
	#include <normal_fragment_maps>
	#include <emissivemap_fragment>
	#include <lights_toon_fragment>
	#include <lights_fragment_begin>
	#include <lights_fragment_maps>
	#include <lights_fragment_end>
	#include <aomap_fragment>
	vec3 outgoingLight = reflectedLight.directDiffuse + reflectedLight.indirectDiffuse + totalEmissiveRadiance;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
	#include <dithering_fragment>
}`,y_=`uniform float size;
uniform float scale;
#include <common>
#include <color_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
#ifdef USE_POINTS_UV
	varying vec2 vUv;
	uniform mat3 uvTransform;
#endif
void main() {
	#ifdef USE_POINTS_UV
		vUv = ( uvTransform * vec3( uv, 1 ) ).xy;
	#endif
	#include <color_vertex>
	#include <morphinstance_vertex>
	#include <morphcolor_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <project_vertex>
	gl_PointSize = size;
	#ifdef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) gl_PointSize *= ( scale / - mvPosition.z );
	#endif
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <worldpos_vertex>
	#include <fog_vertex>
}`,w_=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <color_pars_fragment>
#include <map_particle_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_particle_fragment>
	#include <color_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
	#include <premultiplied_alpha_fragment>
}`,b_=`#include <common>
#include <batching_pars_vertex>
#include <fog_pars_vertex>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <shadowmap_pars_vertex>
void main() {
	#include <batching_vertex>
	#include <beginnormal_vertex>
	#include <morphinstance_vertex>
	#include <morphnormal_vertex>
	#include <skinbase_vertex>
	#include <skinnormal_vertex>
	#include <defaultnormal_vertex>
	#include <begin_vertex>
	#include <morphtarget_vertex>
	#include <skinning_vertex>
	#include <project_vertex>
	#include <logdepthbuf_vertex>
	#include <worldpos_vertex>
	#include <shadowmap_vertex>
	#include <fog_vertex>
}`,M_=`uniform vec3 color;
uniform float opacity;
#include <common>
#include <packing>
#include <fog_pars_fragment>
#include <bsdfs>
#include <lights_pars_begin>
#include <logdepthbuf_pars_fragment>
#include <shadowmap_pars_fragment>
#include <shadowmask_pars_fragment>
void main() {
	#include <logdepthbuf_fragment>
	gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,S_=`uniform float rotation;
uniform vec2 center;
#include <common>
#include <uv_pars_vertex>
#include <fog_pars_vertex>
#include <logdepthbuf_pars_vertex>
#include <clipping_planes_pars_vertex>
void main() {
	#include <uv_vertex>
	vec4 mvPosition = modelViewMatrix[ 3 ];
	vec2 scale = vec2( length( modelMatrix[ 0 ].xyz ), length( modelMatrix[ 1 ].xyz ) );
	#ifndef USE_SIZEATTENUATION
		bool isPerspective = isPerspectiveMatrix( projectionMatrix );
		if ( isPerspective ) scale *= - mvPosition.z;
	#endif
	vec2 alignedPosition = ( position.xy - ( center - vec2( 0.5 ) ) ) * scale;
	vec2 rotatedPosition;
	rotatedPosition.x = cos( rotation ) * alignedPosition.x - sin( rotation ) * alignedPosition.y;
	rotatedPosition.y = sin( rotation ) * alignedPosition.x + cos( rotation ) * alignedPosition.y;
	mvPosition.xy += rotatedPosition;
	gl_Position = projectionMatrix * mvPosition;
	#include <logdepthbuf_vertex>
	#include <clipping_planes_vertex>
	#include <fog_vertex>
}`,T_=`uniform vec3 diffuse;
uniform float opacity;
#include <common>
#include <uv_pars_fragment>
#include <map_pars_fragment>
#include <alphamap_pars_fragment>
#include <alphatest_pars_fragment>
#include <alphahash_pars_fragment>
#include <fog_pars_fragment>
#include <logdepthbuf_pars_fragment>
#include <clipping_planes_pars_fragment>
void main() {
	vec4 diffuseColor = vec4( diffuse, opacity );
	#include <clipping_planes_fragment>
	vec3 outgoingLight = vec3( 0.0 );
	#include <logdepthbuf_fragment>
	#include <map_fragment>
	#include <alphamap_fragment>
	#include <alphatest_fragment>
	#include <alphahash_fragment>
	outgoingLight = diffuseColor.rgb;
	#include <opaque_fragment>
	#include <tonemapping_fragment>
	#include <colorspace_fragment>
	#include <fog_fragment>
}`,Ke={alphahash_fragment:Yp,alphahash_pars_fragment:$p,alphamap_fragment:Zp,alphamap_pars_fragment:Jp,alphatest_fragment:Kp,alphatest_pars_fragment:jp,aomap_fragment:Qp,aomap_pars_fragment:em,batching_pars_vertex:tm,batching_vertex:nm,begin_vertex:im,beginnormal_vertex:sm,bsdfs:rm,iridescence_fragment:am,bumpmap_pars_fragment:om,clipping_planes_fragment:lm,clipping_planes_pars_fragment:cm,clipping_planes_pars_vertex:hm,clipping_planes_vertex:um,color_fragment:dm,color_pars_fragment:fm,color_pars_vertex:pm,color_vertex:mm,common:gm,cube_uv_reflection_fragment:_m,defaultnormal_vertex:xm,displacementmap_pars_vertex:vm,displacementmap_vertex:ym,emissivemap_fragment:wm,emissivemap_pars_fragment:bm,colorspace_fragment:Mm,colorspace_pars_fragment:Sm,envmap_fragment:Tm,envmap_common_pars_fragment:Em,envmap_pars_fragment:Am,envmap_pars_vertex:Cm,envmap_physical_pars_fragment:Bm,envmap_vertex:Rm,fog_vertex:Pm,fog_pars_vertex:Im,fog_fragment:Nm,fog_pars_fragment:Dm,gradientmap_pars_fragment:Lm,lightmap_pars_fragment:Um,lights_lambert_fragment:Fm,lights_lambert_pars_fragment:Om,lights_pars_begin:km,lights_toon_fragment:zm,lights_toon_pars_fragment:Vm,lights_phong_fragment:Hm,lights_phong_pars_fragment:Gm,lights_physical_fragment:Wm,lights_physical_pars_fragment:Xm,lights_fragment_begin:qm,lights_fragment_maps:Ym,lights_fragment_end:$m,logdepthbuf_fragment:Zm,logdepthbuf_pars_fragment:Jm,logdepthbuf_pars_vertex:Km,logdepthbuf_vertex:jm,map_fragment:Qm,map_pars_fragment:eg,map_particle_fragment:tg,map_particle_pars_fragment:ng,metalnessmap_fragment:ig,metalnessmap_pars_fragment:sg,morphinstance_vertex:rg,morphcolor_vertex:ag,morphnormal_vertex:og,morphtarget_pars_vertex:lg,morphtarget_vertex:cg,normal_fragment_begin:hg,normal_fragment_maps:ug,normal_pars_fragment:dg,normal_pars_vertex:fg,normal_vertex:pg,normalmap_pars_fragment:mg,clearcoat_normal_fragment_begin:gg,clearcoat_normal_fragment_maps:_g,clearcoat_pars_fragment:xg,iridescence_pars_fragment:vg,opaque_fragment:yg,packing:wg,premultiplied_alpha_fragment:bg,project_vertex:Mg,dithering_fragment:Sg,dithering_pars_fragment:Tg,roughnessmap_fragment:Eg,roughnessmap_pars_fragment:Ag,shadowmap_pars_fragment:Cg,shadowmap_pars_vertex:Rg,shadowmap_vertex:Pg,shadowmask_pars_fragment:Ig,skinbase_vertex:Ng,skinning_pars_vertex:Dg,skinning_vertex:Lg,skinnormal_vertex:Ug,specularmap_fragment:Fg,specularmap_pars_fragment:Og,tonemapping_fragment:kg,tonemapping_pars_fragment:Bg,transmission_fragment:zg,transmission_pars_fragment:Vg,uv_pars_fragment:Hg,uv_pars_vertex:Gg,uv_vertex:Wg,worldpos_vertex:Xg,background_vert:qg,background_frag:Yg,backgroundCube_vert:$g,backgroundCube_frag:Zg,cube_vert:Jg,cube_frag:Kg,depth_vert:jg,depth_frag:Qg,distanceRGBA_vert:e_,distanceRGBA_frag:t_,equirect_vert:n_,equirect_frag:i_,linedashed_vert:s_,linedashed_frag:r_,meshbasic_vert:a_,meshbasic_frag:o_,meshlambert_vert:l_,meshlambert_frag:c_,meshmatcap_vert:h_,meshmatcap_frag:u_,meshnormal_vert:d_,meshnormal_frag:f_,meshphong_vert:p_,meshphong_frag:m_,meshphysical_vert:g_,meshphysical_frag:__,meshtoon_vert:x_,meshtoon_frag:v_,points_vert:y_,points_frag:w_,shadow_vert:b_,shadow_frag:M_,sprite_vert:S_,sprite_frag:T_},xe={common:{diffuse:{value:new qe(16777215)},opacity:{value:1},map:{value:null},mapTransform:{value:new $e},alphaMap:{value:null},alphaMapTransform:{value:new $e},alphaTest:{value:0}},specularmap:{specularMap:{value:null},specularMapTransform:{value:new $e}},envmap:{envMap:{value:null},envMapRotation:{value:new $e},flipEnvMap:{value:-1},reflectivity:{value:1},ior:{value:1.5},refractionRatio:{value:.98}},aomap:{aoMap:{value:null},aoMapIntensity:{value:1},aoMapTransform:{value:new $e}},lightmap:{lightMap:{value:null},lightMapIntensity:{value:1},lightMapTransform:{value:new $e}},bumpmap:{bumpMap:{value:null},bumpMapTransform:{value:new $e},bumpScale:{value:1}},normalmap:{normalMap:{value:null},normalMapTransform:{value:new $e},normalScale:{value:new de(1,1)}},displacementmap:{displacementMap:{value:null},displacementMapTransform:{value:new $e},displacementScale:{value:1},displacementBias:{value:0}},emissivemap:{emissiveMap:{value:null},emissiveMapTransform:{value:new $e}},metalnessmap:{metalnessMap:{value:null},metalnessMapTransform:{value:new $e}},roughnessmap:{roughnessMap:{value:null},roughnessMapTransform:{value:new $e}},gradientmap:{gradientMap:{value:null}},fog:{fogDensity:{value:25e-5},fogNear:{value:1},fogFar:{value:2e3},fogColor:{value:new qe(16777215)}},lights:{ambientLightColor:{value:[]},lightProbe:{value:[]},directionalLights:{value:[],properties:{direction:{},color:{}}},directionalLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},directionalShadowMap:{value:[]},directionalShadowMatrix:{value:[]},spotLights:{value:[],properties:{color:{},position:{},direction:{},distance:{},coneCos:{},penumbraCos:{},decay:{}}},spotLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{}}},spotLightMap:{value:[]},spotShadowMap:{value:[]},spotLightMatrix:{value:[]},pointLights:{value:[],properties:{color:{},position:{},decay:{},distance:{}}},pointLightShadows:{value:[],properties:{shadowIntensity:1,shadowBias:{},shadowNormalBias:{},shadowRadius:{},shadowMapSize:{},shadowCameraNear:{},shadowCameraFar:{}}},pointShadowMap:{value:[]},pointShadowMatrix:{value:[]},hemisphereLights:{value:[],properties:{direction:{},skyColor:{},groundColor:{}}},rectAreaLights:{value:[],properties:{color:{},position:{},width:{},height:{}}},ltc_1:{value:null},ltc_2:{value:null}},points:{diffuse:{value:new qe(16777215)},opacity:{value:1},size:{value:1},scale:{value:1},map:{value:null},alphaMap:{value:null},alphaMapTransform:{value:new $e},alphaTest:{value:0},uvTransform:{value:new $e}},sprite:{diffuse:{value:new qe(16777215)},opacity:{value:1},center:{value:new de(.5,.5)},rotation:{value:0},map:{value:null},mapTransform:{value:new $e},alphaMap:{value:null},alphaMapTransform:{value:new $e},alphaTest:{value:0}}},Rn={basic:{uniforms:kt([xe.common,xe.specularmap,xe.envmap,xe.aomap,xe.lightmap,xe.fog]),vertexShader:Ke.meshbasic_vert,fragmentShader:Ke.meshbasic_frag},lambert:{uniforms:kt([xe.common,xe.specularmap,xe.envmap,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.fog,xe.lights,{emissive:{value:new qe(0)}}]),vertexShader:Ke.meshlambert_vert,fragmentShader:Ke.meshlambert_frag},phong:{uniforms:kt([xe.common,xe.specularmap,xe.envmap,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.fog,xe.lights,{emissive:{value:new qe(0)},specular:{value:new qe(1118481)},shininess:{value:30}}]),vertexShader:Ke.meshphong_vert,fragmentShader:Ke.meshphong_frag},standard:{uniforms:kt([xe.common,xe.envmap,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.roughnessmap,xe.metalnessmap,xe.fog,xe.lights,{emissive:{value:new qe(0)},roughness:{value:1},metalness:{value:0},envMapIntensity:{value:1}}]),vertexShader:Ke.meshphysical_vert,fragmentShader:Ke.meshphysical_frag},toon:{uniforms:kt([xe.common,xe.aomap,xe.lightmap,xe.emissivemap,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.gradientmap,xe.fog,xe.lights,{emissive:{value:new qe(0)}}]),vertexShader:Ke.meshtoon_vert,fragmentShader:Ke.meshtoon_frag},matcap:{uniforms:kt([xe.common,xe.bumpmap,xe.normalmap,xe.displacementmap,xe.fog,{matcap:{value:null}}]),vertexShader:Ke.meshmatcap_vert,fragmentShader:Ke.meshmatcap_frag},points:{uniforms:kt([xe.points,xe.fog]),vertexShader:Ke.points_vert,fragmentShader:Ke.points_frag},dashed:{uniforms:kt([xe.common,xe.fog,{scale:{value:1},dashSize:{value:1},totalSize:{value:2}}]),vertexShader:Ke.linedashed_vert,fragmentShader:Ke.linedashed_frag},depth:{uniforms:kt([xe.common,xe.displacementmap]),vertexShader:Ke.depth_vert,fragmentShader:Ke.depth_frag},normal:{uniforms:kt([xe.common,xe.bumpmap,xe.normalmap,xe.displacementmap,{opacity:{value:1}}]),vertexShader:Ke.meshnormal_vert,fragmentShader:Ke.meshnormal_frag},sprite:{uniforms:kt([xe.sprite,xe.fog]),vertexShader:Ke.sprite_vert,fragmentShader:Ke.sprite_frag},background:{uniforms:{uvTransform:{value:new $e},t2D:{value:null},backgroundIntensity:{value:1}},vertexShader:Ke.background_vert,fragmentShader:Ke.background_frag},backgroundCube:{uniforms:{envMap:{value:null},flipEnvMap:{value:-1},backgroundBlurriness:{value:0},backgroundIntensity:{value:1},backgroundRotation:{value:new $e}},vertexShader:Ke.backgroundCube_vert,fragmentShader:Ke.backgroundCube_frag},cube:{uniforms:{tCube:{value:null},tFlip:{value:-1},opacity:{value:1}},vertexShader:Ke.cube_vert,fragmentShader:Ke.cube_frag},equirect:{uniforms:{tEquirect:{value:null}},vertexShader:Ke.equirect_vert,fragmentShader:Ke.equirect_frag},distanceRGBA:{uniforms:kt([xe.common,xe.displacementmap,{referencePosition:{value:new N},nearDistance:{value:1},farDistance:{value:1e3}}]),vertexShader:Ke.distanceRGBA_vert,fragmentShader:Ke.distanceRGBA_frag},shadow:{uniforms:kt([xe.lights,xe.fog,{color:{value:new qe(0)},opacity:{value:1}}]),vertexShader:Ke.shadow_vert,fragmentShader:Ke.shadow_frag}};Rn.physical={uniforms:kt([Rn.standard.uniforms,{clearcoat:{value:0},clearcoatMap:{value:null},clearcoatMapTransform:{value:new $e},clearcoatNormalMap:{value:null},clearcoatNormalMapTransform:{value:new $e},clearcoatNormalScale:{value:new de(1,1)},clearcoatRoughness:{value:0},clearcoatRoughnessMap:{value:null},clearcoatRoughnessMapTransform:{value:new $e},dispersion:{value:0},iridescence:{value:0},iridescenceMap:{value:null},iridescenceMapTransform:{value:new $e},iridescenceIOR:{value:1.3},iridescenceThicknessMinimum:{value:100},iridescenceThicknessMaximum:{value:400},iridescenceThicknessMap:{value:null},iridescenceThicknessMapTransform:{value:new $e},sheen:{value:0},sheenColor:{value:new qe(0)},sheenColorMap:{value:null},sheenColorMapTransform:{value:new $e},sheenRoughness:{value:1},sheenRoughnessMap:{value:null},sheenRoughnessMapTransform:{value:new $e},transmission:{value:0},transmissionMap:{value:null},transmissionMapTransform:{value:new $e},transmissionSamplerSize:{value:new de},transmissionSamplerMap:{value:null},thickness:{value:0},thicknessMap:{value:null},thicknessMapTransform:{value:new $e},attenuationDistance:{value:0},attenuationColor:{value:new qe(0)},specularColor:{value:new qe(1,1,1)},specularColorMap:{value:null},specularColorMapTransform:{value:new $e},specularIntensity:{value:1},specularIntensityMap:{value:null},specularIntensityMapTransform:{value:new $e},anisotropyVector:{value:new de},anisotropyMap:{value:null},anisotropyMapTransform:{value:new $e}}]),vertexShader:Ke.meshphysical_vert,fragmentShader:Ke.meshphysical_frag};var Po={r:0,b:0,g:0},ki=new _n,E_=new Mt;function A_(n,e,t,i,s,r,a){let o=new qe(0),c=r===!0?0:1,l,u,h=null,d=0,f=null;function g(M){let y=M.isScene===!0?M.background:null;return y&&y.isTexture&&(y=(M.backgroundBlurriness>0?t:e).get(y)),y}function x(M){let y=!1,R=g(M);R===null?p(o,c):R&&R.isColor&&(p(R,1),y=!0);let E=n.xr.getEnvironmentBlendMode();E==="additive"?i.buffers.color.setClear(0,0,0,1,a):E==="alpha-blend"&&i.buffers.color.setClear(0,0,0,0,a),(n.autoClear||y)&&(i.buffers.depth.setTest(!0),i.buffers.depth.setMask(!0),i.buffers.color.setMask(!0),n.clear(n.autoClearColor,n.autoClearDepth,n.autoClearStencil))}function m(M,y){let R=g(y);R&&(R.isCubeTexture||R.mapping===Mr)?(u===void 0&&(u=new Ot(new oi(1,1,1),new xn({name:"BackgroundCubeMaterial",uniforms:Oi(Rn.backgroundCube.uniforms),vertexShader:Rn.backgroundCube.vertexShader,fragmentShader:Rn.backgroundCube.fragmentShader,side:Wt,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),u.geometry.deleteAttribute("normal"),u.geometry.deleteAttribute("uv"),u.onBeforeRender=function(E,P,D){this.matrixWorld.copyPosition(D.matrixWorld)},Object.defineProperty(u.material,"envMap",{get:function(){return this.uniforms.envMap.value}}),s.update(u)),ki.copy(y.backgroundRotation),ki.x*=-1,ki.y*=-1,ki.z*=-1,R.isCubeTexture&&R.isRenderTargetTexture===!1&&(ki.y*=-1,ki.z*=-1),u.material.uniforms.envMap.value=R,u.material.uniforms.flipEnvMap.value=R.isCubeTexture&&R.isRenderTargetTexture===!1?-1:1,u.material.uniforms.backgroundBlurriness.value=y.backgroundBlurriness,u.material.uniforms.backgroundIntensity.value=y.backgroundIntensity,u.material.uniforms.backgroundRotation.value.setFromMatrix4(E_.makeRotationFromEuler(ki)),u.material.toneMapped=st.getTransfer(R.colorSpace)!==ot,(h!==R||d!==R.version||f!==n.toneMapping)&&(u.material.needsUpdate=!0,h=R,d=R.version,f=n.toneMapping),u.layers.enableAll(),M.unshift(u,u.geometry,u.material,0,0,null)):R&&R.isTexture&&(l===void 0&&(l=new Ot(new gr(2,2),new xn({name:"BackgroundMaterial",uniforms:Oi(Rn.background.uniforms),vertexShader:Rn.background.vertexShader,fragmentShader:Rn.background.fragmentShader,side:Wn,depthTest:!1,depthWrite:!1,fog:!1,allowOverride:!1})),l.geometry.deleteAttribute("normal"),Object.defineProperty(l.material,"map",{get:function(){return this.uniforms.t2D.value}}),s.update(l)),l.material.uniforms.t2D.value=R,l.material.uniforms.backgroundIntensity.value=y.backgroundIntensity,l.material.toneMapped=st.getTransfer(R.colorSpace)!==ot,R.matrixAutoUpdate===!0&&R.updateMatrix(),l.material.uniforms.uvTransform.value.copy(R.matrix),(h!==R||d!==R.version||f!==n.toneMapping)&&(l.material.needsUpdate=!0,h=R,d=R.version,f=n.toneMapping),l.layers.enableAll(),M.unshift(l,l.geometry,l.material,0,0,null))}function p(M,y){M.getRGB(Po,rc(n)),i.buffers.color.setClear(Po.r,Po.g,Po.b,y,a)}function T(){u!==void 0&&(u.geometry.dispose(),u.material.dispose(),u=void 0),l!==void 0&&(l.geometry.dispose(),l.material.dispose(),l=void 0)}return{getClearColor:function(){return o},setClearColor:function(M,y=1){o.set(M),c=y,p(o,c)},getClearAlpha:function(){return c},setClearAlpha:function(M){c=M,p(o,c)},render:x,addToRenderList:m,dispose:T}}function C_(n,e){let t=n.getParameter(n.MAX_VERTEX_ATTRIBS),i={},s=d(null),r=s,a=!1;function o(w,C,k,G,q){let X=!1,V=h(G,k,C);r!==V&&(r=V,l(r.object)),X=f(w,G,k,q),X&&g(w,G,k,q),q!==null&&e.update(q,n.ELEMENT_ARRAY_BUFFER),(X||a)&&(a=!1,y(w,C,k,G),q!==null&&n.bindBuffer(n.ELEMENT_ARRAY_BUFFER,e.get(q).buffer))}function c(){return n.createVertexArray()}function l(w){return n.bindVertexArray(w)}function u(w){return n.deleteVertexArray(w)}function h(w,C,k){let G=k.wireframe===!0,q=i[w.id];q===void 0&&(q={},i[w.id]=q);let X=q[C.id];X===void 0&&(X={},q[C.id]=X);let V=X[G];return V===void 0&&(V=d(c()),X[G]=V),V}function d(w){let C=[],k=[],G=[];for(let q=0;q<t;q++)C[q]=0,k[q]=0,G[q]=0;return{geometry:null,program:null,wireframe:!1,newAttributes:C,enabledAttributes:k,attributeDivisors:G,object:w,attributes:{},index:null}}function f(w,C,k,G){let q=r.attributes,X=C.attributes,V=0,te=k.getAttributes();for(let U in te)if(te[U].location>=0){let he=q[U],ue=X[U];if(ue===void 0&&(U==="instanceMatrix"&&w.instanceMatrix&&(ue=w.instanceMatrix),U==="instanceColor"&&w.instanceColor&&(ue=w.instanceColor)),he===void 0||he.attribute!==ue||ue&&he.data!==ue.data)return!0;V++}return r.attributesNum!==V||r.index!==G}function g(w,C,k,G){let q={},X=C.attributes,V=0,te=k.getAttributes();for(let U in te)if(te[U].location>=0){let he=X[U];he===void 0&&(U==="instanceMatrix"&&w.instanceMatrix&&(he=w.instanceMatrix),U==="instanceColor"&&w.instanceColor&&(he=w.instanceColor));let ue={};ue.attribute=he,he&&he.data&&(ue.data=he.data),q[U]=ue,V++}r.attributes=q,r.attributesNum=V,r.index=G}function x(){let w=r.newAttributes;for(let C=0,k=w.length;C<k;C++)w[C]=0}function m(w){p(w,0)}function p(w,C){let k=r.newAttributes,G=r.enabledAttributes,q=r.attributeDivisors;k[w]=1,G[w]===0&&(n.enableVertexAttribArray(w),G[w]=1),q[w]!==C&&(n.vertexAttribDivisor(w,C),q[w]=C)}function T(){let w=r.newAttributes,C=r.enabledAttributes;for(let k=0,G=C.length;k<G;k++)C[k]!==w[k]&&(n.disableVertexAttribArray(k),C[k]=0)}function M(w,C,k,G,q,X,V){V===!0?n.vertexAttribIPointer(w,C,k,q,X):n.vertexAttribPointer(w,C,k,G,q,X)}function y(w,C,k,G){x();let q=G.attributes,X=k.getAttributes(),V=C.defaultAttributeValues;for(let te in X){let U=X[te];if(U.location>=0){let Q=q[te];if(Q===void 0&&(te==="instanceMatrix"&&w.instanceMatrix&&(Q=w.instanceMatrix),te==="instanceColor"&&w.instanceColor&&(Q=w.instanceColor)),Q!==void 0){let he=Q.normalized,ue=Q.itemSize,ze=e.get(Q);if(ze===void 0)continue;let je=ze.buffer,Qe=ze.type,it=ze.bytesPerElement,Y=Qe===n.INT||Qe===n.UNSIGNED_INT||Q.gpuType===Za;if(Q.isInterleavedBufferAttribute){let se=Q.data,Me=se.stride,Ue=Q.offset;if(se.isInstancedInterleavedBuffer){for(let Ae=0;Ae<U.locationSize;Ae++)p(U.location+Ae,se.meshPerAttribute);w.isInstancedMesh!==!0&&G._maxInstanceCount===void 0&&(G._maxInstanceCount=se.meshPerAttribute*se.count)}else for(let Ae=0;Ae<U.locationSize;Ae++)m(U.location+Ae);n.bindBuffer(n.ARRAY_BUFFER,je);for(let Ae=0;Ae<U.locationSize;Ae++)M(U.location+Ae,ue/U.locationSize,Qe,he,Me*it,(Ue+ue/U.locationSize*Ae)*it,Y)}else{if(Q.isInstancedBufferAttribute){for(let se=0;se<U.locationSize;se++)p(U.location+se,Q.meshPerAttribute);w.isInstancedMesh!==!0&&G._maxInstanceCount===void 0&&(G._maxInstanceCount=Q.meshPerAttribute*Q.count)}else for(let se=0;se<U.locationSize;se++)m(U.location+se);n.bindBuffer(n.ARRAY_BUFFER,je);for(let se=0;se<U.locationSize;se++)M(U.location+se,ue/U.locationSize,Qe,he,ue*it,ue/U.locationSize*se*it,Y)}}else if(V!==void 0){let he=V[te];if(he!==void 0)switch(he.length){case 2:n.vertexAttrib2fv(U.location,he);break;case 3:n.vertexAttrib3fv(U.location,he);break;case 4:n.vertexAttrib4fv(U.location,he);break;default:n.vertexAttrib1fv(U.location,he)}}}}T()}function R(){D();for(let w in i){let C=i[w];for(let k in C){let G=C[k];for(let q in G)u(G[q].object),delete G[q];delete C[k]}delete i[w]}}function E(w){if(i[w.id]===void 0)return;let C=i[w.id];for(let k in C){let G=C[k];for(let q in G)u(G[q].object),delete G[q];delete C[k]}delete i[w.id]}function P(w){for(let C in i){let k=i[C];if(k[w.id]===void 0)continue;let G=k[w.id];for(let q in G)u(G[q].object),delete G[q];delete k[w.id]}}function D(){b(),a=!0,r!==s&&(r=s,l(r.object))}function b(){s.geometry=null,s.program=null,s.wireframe=!1}return{setup:o,reset:D,resetDefaultState:b,dispose:R,releaseStatesOfGeometry:E,releaseStatesOfProgram:P,initAttributes:x,enableAttribute:m,disableUnusedAttributes:T}}function R_(n,e,t){let i;function s(l){i=l}function r(l,u){n.drawArrays(i,l,u),t.update(u,i,1)}function a(l,u,h){h!==0&&(n.drawArraysInstanced(i,l,u,h),t.update(u,i,h))}function o(l,u,h){if(h===0)return;e.get("WEBGL_multi_draw").multiDrawArraysWEBGL(i,l,0,u,0,h);let f=0;for(let g=0;g<h;g++)f+=u[g];t.update(f,i,1)}function c(l,u,h,d){if(h===0)return;let f=e.get("WEBGL_multi_draw");if(f===null)for(let g=0;g<l.length;g++)a(l[g],u[g],d[g]);else{f.multiDrawArraysInstancedWEBGL(i,l,0,u,0,d,0,h);let g=0;for(let x=0;x<h;x++)g+=u[x]*d[x];t.update(g,i,1)}}this.setMode=s,this.render=r,this.renderInstances=a,this.renderMultiDraw=o,this.renderMultiDrawInstances=c}function P_(n,e,t,i){let s;function r(){if(s!==void 0)return s;if(e.has("EXT_texture_filter_anisotropic")===!0){let P=e.get("EXT_texture_filter_anisotropic");s=n.getParameter(P.MAX_TEXTURE_MAX_ANISOTROPY_EXT)}else s=0;return s}function a(P){return!(P!==hn&&i.convert(P)!==n.getParameter(n.IMPLEMENTATION_COLOR_READ_FORMAT))}function o(P){let D=P===ys&&(e.has("EXT_color_buffer_half_float")||e.has("EXT_color_buffer_float"));return!(P!==vn&&i.convert(P)!==n.getParameter(n.IMPLEMENTATION_COLOR_READ_TYPE)&&P!==Cn&&!D)}function c(P){if(P==="highp"){if(n.getShaderPrecisionFormat(n.VERTEX_SHADER,n.HIGH_FLOAT).precision>0&&n.getShaderPrecisionFormat(n.FRAGMENT_SHADER,n.HIGH_FLOAT).precision>0)return"highp";P="mediump"}return P==="mediump"&&n.getShaderPrecisionFormat(n.VERTEX_SHADER,n.MEDIUM_FLOAT).precision>0&&n.getShaderPrecisionFormat(n.FRAGMENT_SHADER,n.MEDIUM_FLOAT).precision>0?"mediump":"lowp"}let l=t.precision!==void 0?t.precision:"highp",u=c(l);u!==l&&(console.warn("THREE.WebGLRenderer:",l,"not supported, using",u,"instead."),l=u);let h=t.logarithmicDepthBuffer===!0,d=t.reversedDepthBuffer===!0&&e.has("EXT_clip_control"),f=n.getParameter(n.MAX_TEXTURE_IMAGE_UNITS),g=n.getParameter(n.MAX_VERTEX_TEXTURE_IMAGE_UNITS),x=n.getParameter(n.MAX_TEXTURE_SIZE),m=n.getParameter(n.MAX_CUBE_MAP_TEXTURE_SIZE),p=n.getParameter(n.MAX_VERTEX_ATTRIBS),T=n.getParameter(n.MAX_VERTEX_UNIFORM_VECTORS),M=n.getParameter(n.MAX_VARYING_VECTORS),y=n.getParameter(n.MAX_FRAGMENT_UNIFORM_VECTORS),R=g>0,E=n.getParameter(n.MAX_SAMPLES);return{isWebGL2:!0,getMaxAnisotropy:r,getMaxPrecision:c,textureFormatReadable:a,textureTypeReadable:o,precision:l,logarithmicDepthBuffer:h,reversedDepthBuffer:d,maxTextures:f,maxVertexTextures:g,maxTextureSize:x,maxCubemapSize:m,maxAttributes:p,maxVertexUniforms:T,maxVaryings:M,maxFragmentUniforms:y,vertexTextures:R,maxSamples:E}}function I_(n){let e=this,t=null,i=0,s=!1,r=!1,a=new an,o=new $e,c={value:null,needsUpdate:!1};this.uniform=c,this.numPlanes=0,this.numIntersection=0,this.init=function(h,d){let f=h.length!==0||d||i!==0||s;return s=d,i=h.length,f},this.beginShadows=function(){r=!0,u(null)},this.endShadows=function(){r=!1},this.setGlobalState=function(h,d){t=u(h,d,0)},this.setState=function(h,d,f){let g=h.clippingPlanes,x=h.clipIntersection,m=h.clipShadows,p=n.get(h);if(!s||g===null||g.length===0||r&&!m)r?u(null):l();else{let T=r?0:i,M=T*4,y=p.clippingState||null;c.value=y,y=u(g,d,M,f);for(let R=0;R!==M;++R)y[R]=t[R];p.clippingState=y,this.numIntersection=x?this.numPlanes:0,this.numPlanes+=T}};function l(){c.value!==t&&(c.value=t,c.needsUpdate=i>0),e.numPlanes=i,e.numIntersection=0}function u(h,d,f,g){let x=h!==null?h.length:0,m=null;if(x!==0){if(m=c.value,g!==!0||m===null){let p=f+x*4,T=d.matrixWorldInverse;o.getNormalMatrix(T),(m===null||m.length<p)&&(m=new Float32Array(p));for(let M=0,y=f;M!==x;++M,y+=4)a.copy(h[M]).applyMatrix4(T,o),a.normal.toArray(m,y),m[y+3]=a.constant}c.value=m,c.needsUpdate=!0}return e.numPlanes=x,e.numIntersection=0,m}}function N_(n){let e=new WeakMap;function t(a,o){return o===qa?a.mapping=Li:o===Ya&&(a.mapping=Ui),a}function i(a){if(a&&a.isTexture){let o=a.mapping;if(o===qa||o===Ya)if(e.has(a)){let c=e.get(a).texture;return t(c,a.mapping)}else{let c=a.image;if(c&&c.height>0){let l=new ya(c.height);return l.fromEquirectangularTexture(n,a),e.set(a,l),a.addEventListener("dispose",s),t(l.texture,a.mapping)}else return null}}return a}function s(a){let o=a.target;o.removeEventListener("dispose",s);let c=e.get(o);c!==void 0&&(e.delete(o),c.dispose())}function r(){e=new WeakMap}return{get:i,dispose:r}}var Ss=4,Hu=[.125,.215,.35,.446,.526,.582],Vi=20,hc=new wr,Gu=new qe,uc=null,dc=0,fc=0,pc=!1,zi=(1+Math.sqrt(5))/2,Ms=1/zi,Wu=[new N(-zi,Ms,0),new N(zi,Ms,0),new N(-Ms,0,zi),new N(Ms,0,zi),new N(0,zi,-Ms),new N(0,zi,Ms),new N(-1,1,-1),new N(1,1,-1),new N(-1,1,1),new N(1,1,1)],D_=new N,Do=class{constructor(e){this._renderer=e,this._pingPongRenderTarget=null,this._lodMax=0,this._cubeSize=0,this._lodPlanes=[],this._sizeLods=[],this._sigmas=[],this._blurMaterial=null,this._cubemapMaterial=null,this._equirectMaterial=null,this._compileMaterial(this._blurMaterial)}fromScene(e,t=0,i=.1,s=100,r={}){let{size:a=256,position:o=D_}=r;uc=this._renderer.getRenderTarget(),dc=this._renderer.getActiveCubeFace(),fc=this._renderer.getActiveMipmapLevel(),pc=this._renderer.xr.enabled,this._renderer.xr.enabled=!1,this._setSize(a);let c=this._allocateTargets();return c.depthBuffer=!0,this._sceneToCubeUV(e,i,s,c,o),t>0&&this._blur(c,0,0,t),this._applyPMREM(c),this._cleanup(c),c}fromEquirectangular(e,t=null){return this._fromTexture(e,t)}fromCubemap(e,t=null){return this._fromTexture(e,t)}compileCubemapShader(){this._cubemapMaterial===null&&(this._cubemapMaterial=Yu(),this._compileMaterial(this._cubemapMaterial))}compileEquirectangularShader(){this._equirectMaterial===null&&(this._equirectMaterial=qu(),this._compileMaterial(this._equirectMaterial))}dispose(){this._dispose(),this._cubemapMaterial!==null&&this._cubemapMaterial.dispose(),this._equirectMaterial!==null&&this._equirectMaterial.dispose()}_setSize(e){this._lodMax=Math.floor(Math.log2(e)),this._cubeSize=Math.pow(2,this._lodMax)}_dispose(){this._blurMaterial!==null&&this._blurMaterial.dispose(),this._pingPongRenderTarget!==null&&this._pingPongRenderTarget.dispose();for(let e=0;e<this._lodPlanes.length;e++)this._lodPlanes[e].dispose()}_cleanup(e){this._renderer.setRenderTarget(uc,dc,fc),this._renderer.xr.enabled=pc,e.scissorTest=!1,Io(e,0,0,e.width,e.height)}_fromTexture(e,t){e.mapping===Li||e.mapping===Ui?this._setSize(e.image.length===0?16:e.image[0].width||e.image[0].image.width):this._setSize(e.image.width/4),uc=this._renderer.getRenderTarget(),dc=this._renderer.getActiveCubeFace(),fc=this._renderer.getActiveMipmapLevel(),pc=this._renderer.xr.enabled,this._renderer.xr.enabled=!1;let i=t||this._allocateTargets();return this._textureToCubeUV(e,i),this._applyPMREM(i),this._cleanup(i),i}_allocateTargets(){let e=3*Math.max(this._cubeSize,112),t=4*this._cubeSize,i={magFilter:gn,minFilter:gn,generateMipmaps:!1,type:ys,format:hn,colorSpace:Ri,depthBuffer:!1},s=Xu(e,t,i);if(this._pingPongRenderTarget===null||this._pingPongRenderTarget.width!==e||this._pingPongRenderTarget.height!==t){this._pingPongRenderTarget!==null&&this._dispose(),this._pingPongRenderTarget=Xu(e,t,i);let{_lodMax:r}=this;({sizeLods:this._sizeLods,lodPlanes:this._lodPlanes,sigmas:this._sigmas}=L_(r)),this._blurMaterial=U_(r,e,t)}return s}_compileMaterial(e){let t=new Ot(this._lodPlanes[0],e);this._renderer.compile(t,hc)}_sceneToCubeUV(e,t,i,s,r){let c=new Ut(90,1,t,i),l=[1,-1,1,1,1,1],u=[1,1,1,-1,-1,-1],h=this._renderer,d=h.autoClear,f=h.toneMapping;h.getClearColor(Gu),h.toneMapping=qn,h.autoClear=!1,h.state.buffers.depth.getReversed()&&(h.setRenderTarget(s),h.clearDepth(),h.setRenderTarget(null));let x=new js({name:"PMREM.Background",side:Wt,depthWrite:!1,depthTest:!1}),m=new Ot(new oi,x),p=!1,T=e.background;T?T.isColor&&(x.color.copy(T),e.background=null,p=!0):(x.color.copy(Gu),p=!0);for(let M=0;M<6;M++){let y=M%3;y===0?(c.up.set(0,l[M],0),c.position.set(r.x,r.y,r.z),c.lookAt(r.x+u[M],r.y,r.z)):y===1?(c.up.set(0,0,l[M]),c.position.set(r.x,r.y,r.z),c.lookAt(r.x,r.y+u[M],r.z)):(c.up.set(0,l[M],0),c.position.set(r.x,r.y,r.z),c.lookAt(r.x,r.y,r.z+u[M]));let R=this._cubeSize;Io(s,y*R,M>2?R:0,R,R),h.setRenderTarget(s),p&&h.render(m,c),h.render(e,c)}m.geometry.dispose(),m.material.dispose(),h.toneMapping=f,h.autoClear=d,e.background=T}_textureToCubeUV(e,t){let i=this._renderer,s=e.mapping===Li||e.mapping===Ui;s?(this._cubemapMaterial===null&&(this._cubemapMaterial=Yu()),this._cubemapMaterial.uniforms.flipEnvMap.value=e.isRenderTargetTexture===!1?-1:1):this._equirectMaterial===null&&(this._equirectMaterial=qu());let r=s?this._cubemapMaterial:this._equirectMaterial,a=new Ot(this._lodPlanes[0],r),o=r.uniforms;o.envMap.value=e;let c=this._cubeSize;Io(t,0,0,3*c,2*c),i.setRenderTarget(t),i.render(a,hc)}_applyPMREM(e){let t=this._renderer,i=t.autoClear;t.autoClear=!1;let s=this._lodPlanes.length;for(let r=1;r<s;r++){let a=Math.sqrt(this._sigmas[r]*this._sigmas[r]-this._sigmas[r-1]*this._sigmas[r-1]),o=Wu[(s-r-1)%Wu.length];this._blur(e,r-1,r,a,o)}t.autoClear=i}_blur(e,t,i,s,r){let a=this._pingPongRenderTarget;this._halfBlur(e,a,t,i,s,"latitudinal",r),this._halfBlur(a,e,i,i,s,"longitudinal",r)}_halfBlur(e,t,i,s,r,a,o){let c=this._renderer,l=this._blurMaterial;a!=="latitudinal"&&a!=="longitudinal"&&console.error("blur direction must be either latitudinal or longitudinal!");let u=3,h=new Ot(this._lodPlanes[s],l),d=l.uniforms,f=this._sizeLods[i]-1,g=isFinite(r)?Math.PI/(2*f):2*Math.PI/(2*Vi-1),x=r/g,m=isFinite(r)?1+Math.floor(u*x):Vi;m>Vi&&console.warn(`sigmaRadians, ${r}, is too large and will clip, as it requested ${m} samples when the maximum is set to ${Vi}`);let p=[],T=0;for(let P=0;P<Vi;++P){let D=P/x,b=Math.exp(-D*D/2);p.push(b),P===0?T+=b:P<m&&(T+=2*b)}for(let P=0;P<p.length;P++)p[P]=p[P]/T;d.envMap.value=e.texture,d.samples.value=m,d.weights.value=p,d.latitudinal.value=a==="latitudinal",o&&(d.poleAxis.value=o);let{_lodMax:M}=this;d.dTheta.value=g,d.mipInt.value=M-i;let y=this._sizeLods[s],R=3*y*(s>M-Ss?s-M+Ss:0),E=4*(this._cubeSize-y);Io(t,R,E,3*y,2*y),c.setRenderTarget(t),c.render(h,hc)}};function L_(n){let e=[],t=[],i=[],s=n,r=n-Ss+1+Hu.length;for(let a=0;a<r;a++){let o=Math.pow(2,s);t.push(o);let c=1/o;a>n-Ss?c=Hu[a-n+Ss-1]:a===0&&(c=0),i.push(c);let l=1/(o-2),u=-l,h=1+l,d=[u,u,h,u,h,h,u,u,h,h,u,h],f=6,g=6,x=3,m=2,p=1,T=new Float32Array(x*g*f),M=new Float32Array(m*g*f),y=new Float32Array(p*g*f);for(let E=0;E<f;E++){let P=E%3*2/3-1,D=E>2?0:-1,b=[P,D,0,P+2/3,D,0,P+2/3,D+1,0,P,D,0,P+2/3,D+1,0,P,D+1,0];T.set(b,x*g*E),M.set(d,m*g*E);let w=[E,E,E,E,E,E];y.set(w,p*g*E)}let R=new cn;R.setAttribute("position",new Nt(T,x)),R.setAttribute("uv",new Nt(M,m)),R.setAttribute("faceIndex",new Nt(y,p)),e.push(R),s>Ss&&s--}return{lodPlanes:e,sizeLods:t,sigmas:i}}function Xu(n,e,t){let i=new Sn(n,e,t);return i.texture.mapping=Mr,i.texture.name="PMREM.cubeUv",i.scissorTest=!0,i}function Io(n,e,t,i,s){n.viewport.set(e,t,i,s),n.scissor.set(e,t,i,s)}function U_(n,e,t){let i=new Float32Array(Vi),s=new N(0,1,0);return new xn({name:"SphericalGaussianBlur",defines:{n:Vi,CUBEUV_TEXEL_WIDTH:1/e,CUBEUV_TEXEL_HEIGHT:1/t,CUBEUV_MAX_MIP:`${n}.0`},uniforms:{envMap:{value:null},samples:{value:1},weights:{value:i},latitudinal:{value:!1},dTheta:{value:0},mipInt:{value:0},poleAxis:{value:s}},vertexShader:Sc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;
			uniform int samples;
			uniform float weights[ n ];
			uniform bool latitudinal;
			uniform float dTheta;
			uniform float mipInt;
			uniform vec3 poleAxis;

			#define ENVMAP_TYPE_CUBE_UV
			#include <cube_uv_reflection_fragment>

			vec3 getSample( float theta, vec3 axis ) {

				float cosTheta = cos( theta );
				// Rodrigues' axis-angle rotation
				vec3 sampleDirection = vOutputDirection * cosTheta
					+ cross( axis, vOutputDirection ) * sin( theta )
					+ axis * dot( axis, vOutputDirection ) * ( 1.0 - cosTheta );

				return bilinearCubeUV( envMap, sampleDirection, mipInt );

			}

			void main() {

				vec3 axis = latitudinal ? poleAxis : cross( poleAxis, vOutputDirection );

				if ( all( equal( axis, vec3( 0.0 ) ) ) ) {

					axis = vec3( vOutputDirection.z, 0.0, - vOutputDirection.x );

				}

				axis = normalize( axis );

				gl_FragColor = vec4( 0.0, 0.0, 0.0, 1.0 );
				gl_FragColor.rgb += weights[ 0 ] * getSample( 0.0, axis );

				for ( int i = 1; i < n; i++ ) {

					if ( i >= samples ) {

						break;

					}

					float theta = dTheta * float( i );
					gl_FragColor.rgb += weights[ i ] * getSample( -1.0 * theta, axis );
					gl_FragColor.rgb += weights[ i ] * getSample( theta, axis );

				}

			}
		`,blending:Xn,depthTest:!1,depthWrite:!1})}function qu(){return new xn({name:"EquirectangularToCubeUV",uniforms:{envMap:{value:null}},vertexShader:Sc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			varying vec3 vOutputDirection;

			uniform sampler2D envMap;

			#include <common>

			void main() {

				vec3 outputDirection = normalize( vOutputDirection );
				vec2 uv = equirectUv( outputDirection );

				gl_FragColor = vec4( texture2D ( envMap, uv ).rgb, 1.0 );

			}
		`,blending:Xn,depthTest:!1,depthWrite:!1})}function Yu(){return new xn({name:"CubemapToCubeUV",uniforms:{envMap:{value:null},flipEnvMap:{value:-1}},vertexShader:Sc(),fragmentShader:`

			precision mediump float;
			precision mediump int;

			uniform float flipEnvMap;

			varying vec3 vOutputDirection;

			uniform samplerCube envMap;

			void main() {

				gl_FragColor = textureCube( envMap, vec3( flipEnvMap * vOutputDirection.x, vOutputDirection.yz ) );

			}
		`,blending:Xn,depthTest:!1,depthWrite:!1})}function Sc(){return`

		precision mediump float;
		precision mediump int;

		attribute float faceIndex;

		varying vec3 vOutputDirection;

		// RH coordinate system; PMREM face-indexing convention
		vec3 getDirection( vec2 uv, float face ) {

			uv = 2.0 * uv - 1.0;

			vec3 direction = vec3( uv, 1.0 );

			if ( face == 0.0 ) {

				direction = direction.zyx; // ( 1, v, u ) pos x

			} else if ( face == 1.0 ) {

				direction = direction.xzy;
				direction.xz *= -1.0; // ( -u, 1, -v ) pos y

			} else if ( face == 2.0 ) {

				direction.x *= -1.0; // ( -u, v, 1 ) pos z

			} else if ( face == 3.0 ) {

				direction = direction.zyx;
				direction.xz *= -1.0; // ( -1, v, -u ) neg x

			} else if ( face == 4.0 ) {

				direction = direction.xzy;
				direction.xy *= -1.0; // ( -u, -1, v ) neg y

			} else if ( face == 5.0 ) {

				direction.z *= -1.0; // ( u, v, -1 ) neg z

			}

			return direction;

		}

		void main() {

			vOutputDirection = getDirection( uv, faceIndex );
			gl_Position = vec4( position, 1.0 );

		}
	`}function F_(n){let e=new WeakMap,t=null;function i(o){if(o&&o.isTexture){let c=o.mapping,l=c===qa||c===Ya,u=c===Li||c===Ui;if(l||u){let h=e.get(o),d=h!==void 0?h.texture.pmremVersion:0;if(o.isRenderTargetTexture&&o.pmremVersion!==d)return t===null&&(t=new Do(n)),h=l?t.fromEquirectangular(o,h):t.fromCubemap(o,h),h.texture.pmremVersion=o.pmremVersion,e.set(o,h),h.texture;if(h!==void 0)return h.texture;{let f=o.image;return l&&f&&f.height>0||u&&f&&s(f)?(t===null&&(t=new Do(n)),h=l?t.fromEquirectangular(o):t.fromCubemap(o),h.texture.pmremVersion=o.pmremVersion,e.set(o,h),o.addEventListener("dispose",r),h.texture):null}}}return o}function s(o){let c=0,l=6;for(let u=0;u<l;u++)o[u]!==void 0&&c++;return c===l}function r(o){let c=o.target;c.removeEventListener("dispose",r);let l=e.get(c);l!==void 0&&(e.delete(c),l.dispose())}function a(){e=new WeakMap,t!==null&&(t.dispose(),t=null)}return{get:i,dispose:a}}function O_(n){let e={};function t(i){if(e[i]!==void 0)return e[i];let s;switch(i){case"WEBGL_depth_texture":s=n.getExtension("WEBGL_depth_texture")||n.getExtension("MOZ_WEBGL_depth_texture")||n.getExtension("WEBKIT_WEBGL_depth_texture");break;case"EXT_texture_filter_anisotropic":s=n.getExtension("EXT_texture_filter_anisotropic")||n.getExtension("MOZ_EXT_texture_filter_anisotropic")||n.getExtension("WEBKIT_EXT_texture_filter_anisotropic");break;case"WEBGL_compressed_texture_s3tc":s=n.getExtension("WEBGL_compressed_texture_s3tc")||n.getExtension("MOZ_WEBGL_compressed_texture_s3tc")||n.getExtension("WEBKIT_WEBGL_compressed_texture_s3tc");break;case"WEBGL_compressed_texture_pvrtc":s=n.getExtension("WEBGL_compressed_texture_pvrtc")||n.getExtension("WEBKIT_WEBGL_compressed_texture_pvrtc");break;default:s=n.getExtension(i)}return e[i]=s,s}return{has:function(i){return t(i)!==null},init:function(){t("EXT_color_buffer_float"),t("WEBGL_clip_cull_distance"),t("OES_texture_float_linear"),t("EXT_color_buffer_half_float"),t("WEBGL_multisampled_render_to_texture"),t("WEBGL_render_shared_exponent")},get:function(i){let s=t(i);return s===null&&hs("THREE.WebGLRenderer: "+i+" extension not supported."),s}}}function k_(n,e,t,i){let s={},r=new WeakMap;function a(h){let d=h.target;d.index!==null&&e.remove(d.index);for(let g in d.attributes)e.remove(d.attributes[g]);d.removeEventListener("dispose",a),delete s[d.id];let f=r.get(d);f&&(e.remove(f),r.delete(d)),i.releaseStatesOfGeometry(d),d.isInstancedBufferGeometry===!0&&delete d._maxInstanceCount,t.memory.geometries--}function o(h,d){return s[d.id]===!0||(d.addEventListener("dispose",a),s[d.id]=!0,t.memory.geometries++),d}function c(h){let d=h.attributes;for(let f in d)e.update(d[f],n.ARRAY_BUFFER)}function l(h){let d=[],f=h.index,g=h.attributes.position,x=0;if(f!==null){let T=f.array;x=f.version;for(let M=0,y=T.length;M<y;M+=3){let R=T[M+0],E=T[M+1],P=T[M+2];d.push(R,E,E,P,P,R)}}else if(g!==void 0){let T=g.array;x=g.version;for(let M=0,y=T.length/3-1;M<y;M+=3){let R=M+0,E=M+1,P=M+2;d.push(R,E,E,P,P,R)}}else return;let m=new(sc(d)?er:Qs)(d,1);m.version=x;let p=r.get(h);p&&e.remove(p),r.set(h,m)}function u(h){let d=r.get(h);if(d){let f=h.index;f!==null&&d.version<f.version&&l(h)}else l(h);return r.get(h)}return{get:o,update:c,getWireframeAttribute:u}}function B_(n,e,t){let i;function s(d){i=d}let r,a;function o(d){r=d.type,a=d.bytesPerElement}function c(d,f){n.drawElements(i,f,r,d*a),t.update(f,i,1)}function l(d,f,g){g!==0&&(n.drawElementsInstanced(i,f,r,d*a,g),t.update(f,i,g))}function u(d,f,g){if(g===0)return;e.get("WEBGL_multi_draw").multiDrawElementsWEBGL(i,f,0,r,d,0,g);let m=0;for(let p=0;p<g;p++)m+=f[p];t.update(m,i,1)}function h(d,f,g,x){if(g===0)return;let m=e.get("WEBGL_multi_draw");if(m===null)for(let p=0;p<d.length;p++)l(d[p]/a,f[p],x[p]);else{m.multiDrawElementsInstancedWEBGL(i,f,0,r,d,0,x,0,g);let p=0;for(let T=0;T<g;T++)p+=f[T]*x[T];t.update(p,i,1)}}this.setMode=s,this.setIndex=o,this.render=c,this.renderInstances=l,this.renderMultiDraw=u,this.renderMultiDrawInstances=h}function z_(n){let e={geometries:0,textures:0},t={frame:0,calls:0,triangles:0,points:0,lines:0};function i(r,a,o){switch(t.calls++,a){case n.TRIANGLES:t.triangles+=o*(r/3);break;case n.LINES:t.lines+=o*(r/2);break;case n.LINE_STRIP:t.lines+=o*(r-1);break;case n.LINE_LOOP:t.lines+=o*r;break;case n.POINTS:t.points+=o*r;break;default:console.error("THREE.WebGLInfo: Unknown draw mode:",a);break}}function s(){t.calls=0,t.triangles=0,t.points=0,t.lines=0}return{memory:e,render:t,programs:null,autoReset:!0,reset:s,update:i}}function V_(n,e,t){let i=new WeakMap,s=new wt;function r(a,o,c){let l=a.morphTargetInfluences,u=o.morphAttributes.position||o.morphAttributes.normal||o.morphAttributes.color,h=u!==void 0?u.length:0,d=i.get(o);if(d===void 0||d.count!==h){let b=function(){P.dispose(),i.delete(o),o.removeEventListener("dispose",b)};d!==void 0&&d.texture.dispose();let f=o.morphAttributes.position!==void 0,g=o.morphAttributes.normal!==void 0,x=o.morphAttributes.color!==void 0,m=o.morphAttributes.position||[],p=o.morphAttributes.normal||[],T=o.morphAttributes.color||[],M=0;f===!0&&(M=1),g===!0&&(M=2),x===!0&&(M=3);let y=o.attributes.position.count*M,R=1;y>e.maxTextureSize&&(R=Math.ceil(y/e.maxTextureSize),y=e.maxTextureSize);let E=new Float32Array(y*R*4*h),P=new Js(E,y,R,h);P.type=Cn,P.needsUpdate=!0;let D=M*4;for(let w=0;w<h;w++){let C=m[w],k=p[w],G=T[w],q=y*R*4*w;for(let X=0;X<C.count;X++){let V=X*D;f===!0&&(s.fromBufferAttribute(C,X),E[q+V+0]=s.x,E[q+V+1]=s.y,E[q+V+2]=s.z,E[q+V+3]=0),g===!0&&(s.fromBufferAttribute(k,X),E[q+V+4]=s.x,E[q+V+5]=s.y,E[q+V+6]=s.z,E[q+V+7]=0),x===!0&&(s.fromBufferAttribute(G,X),E[q+V+8]=s.x,E[q+V+9]=s.y,E[q+V+10]=s.z,E[q+V+11]=G.itemSize===4?s.w:1)}}d={count:h,texture:P,size:new de(y,R)},i.set(o,d),o.addEventListener("dispose",b)}if(a.isInstancedMesh===!0&&a.morphTexture!==null)c.getUniforms().setValue(n,"morphTexture",a.morphTexture,t);else{let f=0;for(let x=0;x<l.length;x++)f+=l[x];let g=o.morphTargetsRelative?1:1-f;c.getUniforms().setValue(n,"morphTargetBaseInfluence",g),c.getUniforms().setValue(n,"morphTargetInfluences",l)}c.getUniforms().setValue(n,"morphTargetsTexture",d.texture,t),c.getUniforms().setValue(n,"morphTargetsTextureSize",d.size)}return{update:r}}function H_(n,e,t,i){let s=new WeakMap;function r(c){let l=i.render.frame,u=c.geometry,h=e.get(c,u);if(s.get(h)!==l&&(e.update(h),s.set(h,l)),c.isInstancedMesh&&(c.hasEventListener("dispose",o)===!1&&c.addEventListener("dispose",o),s.get(c)!==l&&(t.update(c.instanceMatrix,n.ARRAY_BUFFER),c.instanceColor!==null&&t.update(c.instanceColor,n.ARRAY_BUFFER),s.set(c,l))),c.isSkinnedMesh){let d=c.skeleton;s.get(d)!==l&&(d.update(),s.set(d,l))}return h}function a(){s=new WeakMap}function o(c){let l=c.target;l.removeEventListener("dispose",o),t.remove(l.instanceMatrix),l.instanceColor!==null&&t.remove(l.instanceColor)}return{update:r,dispose:a}}var dd=new Yt,$u=new rr(1,1),fd=new Js,pd=new xa,md=new nr,Zu=[],Ju=[],Ku=new Float32Array(16),ju=new Float32Array(9),Qu=new Float32Array(4);function Es(n,e,t){let i=n[0];if(i<=0||i>0)return n;let s=e*t,r=Zu[s];if(r===void 0&&(r=new Float32Array(s),Zu[s]=r),e!==0){i.toArray(r,0);for(let a=1,o=0;a!==e;++a)o+=t,n[a].toArray(r,o)}return r}function Et(n,e){if(n.length!==e.length)return!1;for(let t=0,i=n.length;t<i;t++)if(n[t]!==e[t])return!1;return!0}function At(n,e){for(let t=0,i=e.length;t<i;t++)n[t]=e[t]}function Uo(n,e){let t=Ju[e];t===void 0&&(t=new Int32Array(e),Ju[e]=t);for(let i=0;i!==e;++i)t[i]=n.allocateTextureUnit();return t}function G_(n,e){let t=this.cache;t[0]!==e&&(n.uniform1f(this.addr,e),t[0]=e)}function W_(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(n.uniform2f(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Et(t,e))return;n.uniform2fv(this.addr,e),At(t,e)}}function X_(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(n.uniform3f(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else if(e.r!==void 0)(t[0]!==e.r||t[1]!==e.g||t[2]!==e.b)&&(n.uniform3f(this.addr,e.r,e.g,e.b),t[0]=e.r,t[1]=e.g,t[2]=e.b);else{if(Et(t,e))return;n.uniform3fv(this.addr,e),At(t,e)}}function q_(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(n.uniform4f(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Et(t,e))return;n.uniform4fv(this.addr,e),At(t,e)}}function Y_(n,e){let t=this.cache,i=e.elements;if(i===void 0){if(Et(t,e))return;n.uniformMatrix2fv(this.addr,!1,e),At(t,e)}else{if(Et(t,i))return;Qu.set(i),n.uniformMatrix2fv(this.addr,!1,Qu),At(t,i)}}function $_(n,e){let t=this.cache,i=e.elements;if(i===void 0){if(Et(t,e))return;n.uniformMatrix3fv(this.addr,!1,e),At(t,e)}else{if(Et(t,i))return;ju.set(i),n.uniformMatrix3fv(this.addr,!1,ju),At(t,i)}}function Z_(n,e){let t=this.cache,i=e.elements;if(i===void 0){if(Et(t,e))return;n.uniformMatrix4fv(this.addr,!1,e),At(t,e)}else{if(Et(t,i))return;Ku.set(i),n.uniformMatrix4fv(this.addr,!1,Ku),At(t,i)}}function J_(n,e){let t=this.cache;t[0]!==e&&(n.uniform1i(this.addr,e),t[0]=e)}function K_(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(n.uniform2i(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Et(t,e))return;n.uniform2iv(this.addr,e),At(t,e)}}function j_(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(n.uniform3i(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Et(t,e))return;n.uniform3iv(this.addr,e),At(t,e)}}function Q_(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(n.uniform4i(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Et(t,e))return;n.uniform4iv(this.addr,e),At(t,e)}}function ex(n,e){let t=this.cache;t[0]!==e&&(n.uniform1ui(this.addr,e),t[0]=e)}function tx(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y)&&(n.uniform2ui(this.addr,e.x,e.y),t[0]=e.x,t[1]=e.y);else{if(Et(t,e))return;n.uniform2uiv(this.addr,e),At(t,e)}}function nx(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z)&&(n.uniform3ui(this.addr,e.x,e.y,e.z),t[0]=e.x,t[1]=e.y,t[2]=e.z);else{if(Et(t,e))return;n.uniform3uiv(this.addr,e),At(t,e)}}function ix(n,e){let t=this.cache;if(e.x!==void 0)(t[0]!==e.x||t[1]!==e.y||t[2]!==e.z||t[3]!==e.w)&&(n.uniform4ui(this.addr,e.x,e.y,e.z,e.w),t[0]=e.x,t[1]=e.y,t[2]=e.z,t[3]=e.w);else{if(Et(t,e))return;n.uniform4uiv(this.addr,e),At(t,e)}}function sx(n,e,t){let i=this.cache,s=t.allocateTextureUnit();i[0]!==s&&(n.uniform1i(this.addr,s),i[0]=s);let r;this.type===n.SAMPLER_2D_SHADOW?($u.compareFunction=ec,r=$u):r=dd,t.setTexture2D(e||r,s)}function rx(n,e,t){let i=this.cache,s=t.allocateTextureUnit();i[0]!==s&&(n.uniform1i(this.addr,s),i[0]=s),t.setTexture3D(e||pd,s)}function ax(n,e,t){let i=this.cache,s=t.allocateTextureUnit();i[0]!==s&&(n.uniform1i(this.addr,s),i[0]=s),t.setTextureCube(e||md,s)}function ox(n,e,t){let i=this.cache,s=t.allocateTextureUnit();i[0]!==s&&(n.uniform1i(this.addr,s),i[0]=s),t.setTexture2DArray(e||fd,s)}function lx(n){switch(n){case 5126:return G_;case 35664:return W_;case 35665:return X_;case 35666:return q_;case 35674:return Y_;case 35675:return $_;case 35676:return Z_;case 5124:case 35670:return J_;case 35667:case 35671:return K_;case 35668:case 35672:return j_;case 35669:case 35673:return Q_;case 5125:return ex;case 36294:return tx;case 36295:return nx;case 36296:return ix;case 35678:case 36198:case 36298:case 36306:case 35682:return sx;case 35679:case 36299:case 36307:return rx;case 35680:case 36300:case 36308:case 36293:return ax;case 36289:case 36303:case 36311:case 36292:return ox}}function cx(n,e){n.uniform1fv(this.addr,e)}function hx(n,e){let t=Es(e,this.size,2);n.uniform2fv(this.addr,t)}function ux(n,e){let t=Es(e,this.size,3);n.uniform3fv(this.addr,t)}function dx(n,e){let t=Es(e,this.size,4);n.uniform4fv(this.addr,t)}function fx(n,e){let t=Es(e,this.size,4);n.uniformMatrix2fv(this.addr,!1,t)}function px(n,e){let t=Es(e,this.size,9);n.uniformMatrix3fv(this.addr,!1,t)}function mx(n,e){let t=Es(e,this.size,16);n.uniformMatrix4fv(this.addr,!1,t)}function gx(n,e){n.uniform1iv(this.addr,e)}function _x(n,e){n.uniform2iv(this.addr,e)}function xx(n,e){n.uniform3iv(this.addr,e)}function vx(n,e){n.uniform4iv(this.addr,e)}function yx(n,e){n.uniform1uiv(this.addr,e)}function wx(n,e){n.uniform2uiv(this.addr,e)}function bx(n,e){n.uniform3uiv(this.addr,e)}function Mx(n,e){n.uniform4uiv(this.addr,e)}function Sx(n,e,t){let i=this.cache,s=e.length,r=Uo(t,s);Et(i,r)||(n.uniform1iv(this.addr,r),At(i,r));for(let a=0;a!==s;++a)t.setTexture2D(e[a]||dd,r[a])}function Tx(n,e,t){let i=this.cache,s=e.length,r=Uo(t,s);Et(i,r)||(n.uniform1iv(this.addr,r),At(i,r));for(let a=0;a!==s;++a)t.setTexture3D(e[a]||pd,r[a])}function Ex(n,e,t){let i=this.cache,s=e.length,r=Uo(t,s);Et(i,r)||(n.uniform1iv(this.addr,r),At(i,r));for(let a=0;a!==s;++a)t.setTextureCube(e[a]||md,r[a])}function Ax(n,e,t){let i=this.cache,s=e.length,r=Uo(t,s);Et(i,r)||(n.uniform1iv(this.addr,r),At(i,r));for(let a=0;a!==s;++a)t.setTexture2DArray(e[a]||fd,r[a])}function Cx(n){switch(n){case 5126:return cx;case 35664:return hx;case 35665:return ux;case 35666:return dx;case 35674:return fx;case 35675:return px;case 35676:return mx;case 5124:case 35670:return gx;case 35667:case 35671:return _x;case 35668:case 35672:return xx;case 35669:case 35673:return vx;case 5125:return yx;case 36294:return wx;case 36295:return bx;case 36296:return Mx;case 35678:case 36198:case 36298:case 36306:case 35682:return Sx;case 35679:case 36299:case 36307:return Tx;case 35680:case 36300:case 36308:case 36293:return Ex;case 36289:case 36303:case 36311:case 36292:return Ax}}var gc=class{constructor(e,t,i){this.id=e,this.addr=i,this.cache=[],this.type=t.type,this.setValue=lx(t.type)}},_c=class{constructor(e,t,i){this.id=e,this.addr=i,this.cache=[],this.type=t.type,this.size=t.size,this.setValue=Cx(t.type)}},xc=class{constructor(e){this.id=e,this.seq=[],this.map={}}setValue(e,t,i){let s=this.seq;for(let r=0,a=s.length;r!==a;++r){let o=s[r];o.setValue(e,t[o.id],i)}}},mc=/(\w+)(\])?(\[|\.)?/g;function ed(n,e){n.seq.push(e),n.map[e.id]=e}function Rx(n,e,t){let i=n.name,s=i.length;for(mc.lastIndex=0;;){let r=mc.exec(i),a=mc.lastIndex,o=r[1],c=r[2]==="]",l=r[3];if(c&&(o=o|0),l===void 0||l==="["&&a+2===s){ed(t,l===void 0?new gc(o,n,e):new _c(o,n,e));break}else{let h=t.map[o];h===void 0&&(h=new xc(o),ed(t,h)),t=h}}}var Ts=class{constructor(e,t){this.seq=[],this.map={};let i=e.getProgramParameter(t,e.ACTIVE_UNIFORMS);for(let s=0;s<i;++s){let r=e.getActiveUniform(t,s),a=e.getUniformLocation(t,r.name);Rx(r,a,this)}}setValue(e,t,i,s){let r=this.map[t];r!==void 0&&r.setValue(e,i,s)}setOptional(e,t,i){let s=t[i];s!==void 0&&this.setValue(e,i,s)}static upload(e,t,i,s){for(let r=0,a=t.length;r!==a;++r){let o=t[r],c=i[o.id];c.needsUpdate!==!1&&o.setValue(e,c.value,s)}}static seqWithValue(e,t){let i=[];for(let s=0,r=e.length;s!==r;++s){let a=e[s];a.id in t&&i.push(a)}return i}};function td(n,e,t){let i=n.createShader(e);return n.shaderSource(i,t),n.compileShader(i),i}var Px=37297,Ix=0;function Nx(n,e){let t=n.split(`
`),i=[],s=Math.max(e-6,0),r=Math.min(e+6,t.length);for(let a=s;a<r;a++){let o=a+1;i.push(`${o===e?">":" "} ${o}: ${t[a]}`)}return i.join(`
`)}var nd=new $e;function Dx(n){st._getMatrix(nd,st.workingColorSpace,n);let e=`mat3( ${nd.elements.map(t=>t.toFixed(4))} )`;switch(st.getTransfer(n)){case Ys:return[e,"LinearTransferOETF"];case ot:return[e,"sRGBTransferOETF"];default:return console.warn("THREE.WebGLProgram: Unsupported color space: ",n),[e,"LinearTransferOETF"]}}function id(n,e,t){let i=n.getShaderParameter(e,n.COMPILE_STATUS),r=(n.getShaderInfoLog(e)||"").trim();if(i&&r==="")return"";let a=/ERROR: 0:(\d+)/.exec(r);if(a){let o=parseInt(a[1]);return t.toUpperCase()+`

`+r+`

`+Nx(n.getShaderSource(e),o)}else return r}function Lx(n,e){let t=Dx(e);return[`vec4 ${n}( vec4 value ) {`,`	return ${t[1]}( vec4( value.rgb * ${t[0]}, value.a ) );`,"}"].join(`
`)}function Ux(n,e){let t;switch(e){case mu:t="Linear";break;case gu:t="Reinhard";break;case _u:t="Cineon";break;case xu:t="ACESFilmic";break;case yu:t="AgX";break;case wu:t="Neutral";break;case vu:t="Custom";break;default:console.warn("THREE.WebGLProgram: Unsupported toneMapping:",e),t="Linear"}return"vec3 "+n+"( vec3 color ) { return "+t+"ToneMapping( color ); }"}var No=new N;function Fx(){st.getLuminanceCoefficients(No);let n=No.x.toFixed(4),e=No.y.toFixed(4),t=No.z.toFixed(4);return["float luminance( const in vec3 rgb ) {",`	const vec3 weights = vec3( ${n}, ${e}, ${t} );`,"	return dot( weights, rgb );","}"].join(`
`)}function Ox(n){return[n.extensionClipCullDistance?"#extension GL_ANGLE_clip_cull_distance : require":"",n.extensionMultiDraw?"#extension GL_ANGLE_multi_draw : require":""].filter(Rr).join(`
`)}function kx(n){let e=[];for(let t in n){let i=n[t];i!==!1&&e.push("#define "+t+" "+i)}return e.join(`
`)}function Bx(n,e){let t={},i=n.getProgramParameter(e,n.ACTIVE_ATTRIBUTES);for(let s=0;s<i;s++){let r=n.getActiveAttrib(e,s),a=r.name,o=1;r.type===n.FLOAT_MAT2&&(o=2),r.type===n.FLOAT_MAT3&&(o=3),r.type===n.FLOAT_MAT4&&(o=4),t[a]={type:r.type,location:n.getAttribLocation(e,a),locationSize:o}}return t}function Rr(n){return n!==""}function sd(n,e){let t=e.numSpotLightShadows+e.numSpotLightMaps-e.numSpotLightShadowsWithMaps;return n.replace(/NUM_DIR_LIGHTS/g,e.numDirLights).replace(/NUM_SPOT_LIGHTS/g,e.numSpotLights).replace(/NUM_SPOT_LIGHT_MAPS/g,e.numSpotLightMaps).replace(/NUM_SPOT_LIGHT_COORDS/g,t).replace(/NUM_RECT_AREA_LIGHTS/g,e.numRectAreaLights).replace(/NUM_POINT_LIGHTS/g,e.numPointLights).replace(/NUM_HEMI_LIGHTS/g,e.numHemiLights).replace(/NUM_DIR_LIGHT_SHADOWS/g,e.numDirLightShadows).replace(/NUM_SPOT_LIGHT_SHADOWS_WITH_MAPS/g,e.numSpotLightShadowsWithMaps).replace(/NUM_SPOT_LIGHT_SHADOWS/g,e.numSpotLightShadows).replace(/NUM_POINT_LIGHT_SHADOWS/g,e.numPointLightShadows)}function rd(n,e){return n.replace(/NUM_CLIPPING_PLANES/g,e.numClippingPlanes).replace(/UNION_CLIPPING_PLANES/g,e.numClippingPlanes-e.numClipIntersection)}var zx=/^[ \t]*#include +<([\w\d./]+)>/gm;function vc(n){return n.replace(zx,Hx)}var Vx=new Map;function Hx(n,e){let t=Ke[e];if(t===void 0){let i=Vx.get(e);if(i!==void 0)t=Ke[i],console.warn('THREE.WebGLRenderer: Shader chunk "%s" has been deprecated. Use "%s" instead.',e,i);else throw new Error("Can not resolve #include <"+e+">")}return vc(t)}var Gx=/#pragma unroll_loop_start\s+for\s*\(\s*int\s+i\s*=\s*(\d+)\s*;\s*i\s*<\s*(\d+)\s*;\s*i\s*\+\+\s*\)\s*{([\s\S]+?)}\s+#pragma unroll_loop_end/g;function ad(n){return n.replace(Gx,Wx)}function Wx(n,e,t,i){let s="";for(let r=parseInt(e);r<parseInt(t);r++)s+=i.replace(/\[\s*i\s*\]/g,"[ "+r+" ]").replace(/UNROLLED_LOOP_INDEX/g,r);return s}function od(n){let e=`precision ${n.precision} float;
	precision ${n.precision} int;
	precision ${n.precision} sampler2D;
	precision ${n.precision} samplerCube;
	precision ${n.precision} sampler3D;
	precision ${n.precision} sampler2DArray;
	precision ${n.precision} sampler2DShadow;
	precision ${n.precision} samplerCubeShadow;
	precision ${n.precision} sampler2DArrayShadow;
	precision ${n.precision} isampler2D;
	precision ${n.precision} isampler3D;
	precision ${n.precision} isamplerCube;
	precision ${n.precision} isampler2DArray;
	precision ${n.precision} usampler2D;
	precision ${n.precision} usampler3D;
	precision ${n.precision} usamplerCube;
	precision ${n.precision} usampler2DArray;
	`;return n.precision==="highp"?e+=`
#define HIGH_PRECISION`:n.precision==="mediump"?e+=`
#define MEDIUM_PRECISION`:n.precision==="lowp"&&(e+=`
#define LOW_PRECISION`),e}function Xx(n){let e="SHADOWMAP_TYPE_BASIC";return n.shadowMapType===Bl?e="SHADOWMAP_TYPE_PCF":n.shadowMapType===ka?e="SHADOWMAP_TYPE_PCF_SOFT":n.shadowMapType===En&&(e="SHADOWMAP_TYPE_VSM"),e}function qx(n){let e="ENVMAP_TYPE_CUBE";if(n.envMap)switch(n.envMapMode){case Li:case Ui:e="ENVMAP_TYPE_CUBE";break;case Mr:e="ENVMAP_TYPE_CUBE_UV";break}return e}function Yx(n){let e="ENVMAP_MODE_REFLECTION";return n.envMap&&n.envMapMode===Ui&&(e="ENVMAP_MODE_REFRACTION"),e}function $x(n){let e="ENVMAP_BLENDING_NONE";if(n.envMap)switch(n.combine){case Gl:e="ENVMAP_BLENDING_MULTIPLY";break;case fu:e="ENVMAP_BLENDING_MIX";break;case pu:e="ENVMAP_BLENDING_ADD";break}return e}function Zx(n){let e=n.envMapCubeUVHeight;if(e===null)return null;let t=Math.log2(e)-2,i=1/e;return{texelWidth:1/(3*Math.max(Math.pow(2,t),112)),texelHeight:i,maxMip:t}}function Jx(n,e,t,i){let s=n.getContext(),r=t.defines,a=t.vertexShader,o=t.fragmentShader,c=Xx(t),l=qx(t),u=Yx(t),h=$x(t),d=Zx(t),f=Ox(t),g=kx(r),x=s.createProgram(),m,p,T=t.glslVersion?"#version "+t.glslVersion+`
`:"";t.isRawShaderMaterial?(m=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g].filter(Rr).join(`
`),m.length>0&&(m+=`
`),p=["#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g].filter(Rr).join(`
`),p.length>0&&(p+=`
`)):(m=[od(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g,t.extensionClipCullDistance?"#define USE_CLIP_DISTANCE":"",t.batching?"#define USE_BATCHING":"",t.batchingColor?"#define USE_BATCHING_COLOR":"",t.instancing?"#define USE_INSTANCING":"",t.instancingColor?"#define USE_INSTANCING_COLOR":"",t.instancingMorph?"#define USE_INSTANCING_MORPH":"",t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.map?"#define USE_MAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+u:"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.displacementMap?"#define USE_DISPLACEMENTMAP":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.mapUv?"#define MAP_UV "+t.mapUv:"",t.alphaMapUv?"#define ALPHAMAP_UV "+t.alphaMapUv:"",t.lightMapUv?"#define LIGHTMAP_UV "+t.lightMapUv:"",t.aoMapUv?"#define AOMAP_UV "+t.aoMapUv:"",t.emissiveMapUv?"#define EMISSIVEMAP_UV "+t.emissiveMapUv:"",t.bumpMapUv?"#define BUMPMAP_UV "+t.bumpMapUv:"",t.normalMapUv?"#define NORMALMAP_UV "+t.normalMapUv:"",t.displacementMapUv?"#define DISPLACEMENTMAP_UV "+t.displacementMapUv:"",t.metalnessMapUv?"#define METALNESSMAP_UV "+t.metalnessMapUv:"",t.roughnessMapUv?"#define ROUGHNESSMAP_UV "+t.roughnessMapUv:"",t.anisotropyMapUv?"#define ANISOTROPYMAP_UV "+t.anisotropyMapUv:"",t.clearcoatMapUv?"#define CLEARCOATMAP_UV "+t.clearcoatMapUv:"",t.clearcoatNormalMapUv?"#define CLEARCOAT_NORMALMAP_UV "+t.clearcoatNormalMapUv:"",t.clearcoatRoughnessMapUv?"#define CLEARCOAT_ROUGHNESSMAP_UV "+t.clearcoatRoughnessMapUv:"",t.iridescenceMapUv?"#define IRIDESCENCEMAP_UV "+t.iridescenceMapUv:"",t.iridescenceThicknessMapUv?"#define IRIDESCENCE_THICKNESSMAP_UV "+t.iridescenceThicknessMapUv:"",t.sheenColorMapUv?"#define SHEEN_COLORMAP_UV "+t.sheenColorMapUv:"",t.sheenRoughnessMapUv?"#define SHEEN_ROUGHNESSMAP_UV "+t.sheenRoughnessMapUv:"",t.specularMapUv?"#define SPECULARMAP_UV "+t.specularMapUv:"",t.specularColorMapUv?"#define SPECULAR_COLORMAP_UV "+t.specularColorMapUv:"",t.specularIntensityMapUv?"#define SPECULAR_INTENSITYMAP_UV "+t.specularIntensityMapUv:"",t.transmissionMapUv?"#define TRANSMISSIONMAP_UV "+t.transmissionMapUv:"",t.thicknessMapUv?"#define THICKNESSMAP_UV "+t.thicknessMapUv:"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.flatShading?"#define FLAT_SHADED":"",t.skinning?"#define USE_SKINNING":"",t.morphTargets?"#define USE_MORPHTARGETS":"",t.morphNormals&&t.flatShading===!1?"#define USE_MORPHNORMALS":"",t.morphColors?"#define USE_MORPHCOLORS":"",t.morphTargetsCount>0?"#define MORPHTARGETS_TEXTURE_STRIDE "+t.morphTextureStride:"",t.morphTargetsCount>0?"#define MORPHTARGETS_COUNT "+t.morphTargetsCount:"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+c:"",t.sizeAttenuation?"#define USE_SIZEATTENUATION":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",t.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 modelMatrix;","uniform mat4 modelViewMatrix;","uniform mat4 projectionMatrix;","uniform mat4 viewMatrix;","uniform mat3 normalMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;","#ifdef USE_INSTANCING","	attribute mat4 instanceMatrix;","#endif","#ifdef USE_INSTANCING_COLOR","	attribute vec3 instanceColor;","#endif","#ifdef USE_INSTANCING_MORPH","	uniform sampler2D morphTexture;","#endif","attribute vec3 position;","attribute vec3 normal;","attribute vec2 uv;","#ifdef USE_UV1","	attribute vec2 uv1;","#endif","#ifdef USE_UV2","	attribute vec2 uv2;","#endif","#ifdef USE_UV3","	attribute vec2 uv3;","#endif","#ifdef USE_TANGENT","	attribute vec4 tangent;","#endif","#if defined( USE_COLOR_ALPHA )","	attribute vec4 color;","#elif defined( USE_COLOR )","	attribute vec3 color;","#endif","#ifdef USE_SKINNING","	attribute vec4 skinIndex;","	attribute vec4 skinWeight;","#endif",`
`].filter(Rr).join(`
`),p=[od(t),"#define SHADER_TYPE "+t.shaderType,"#define SHADER_NAME "+t.shaderName,g,t.useFog&&t.fog?"#define USE_FOG":"",t.useFog&&t.fogExp2?"#define FOG_EXP2":"",t.alphaToCoverage?"#define ALPHA_TO_COVERAGE":"",t.map?"#define USE_MAP":"",t.matcap?"#define USE_MATCAP":"",t.envMap?"#define USE_ENVMAP":"",t.envMap?"#define "+l:"",t.envMap?"#define "+u:"",t.envMap?"#define "+h:"",d?"#define CUBEUV_TEXEL_WIDTH "+d.texelWidth:"",d?"#define CUBEUV_TEXEL_HEIGHT "+d.texelHeight:"",d?"#define CUBEUV_MAX_MIP "+d.maxMip+".0":"",t.lightMap?"#define USE_LIGHTMAP":"",t.aoMap?"#define USE_AOMAP":"",t.bumpMap?"#define USE_BUMPMAP":"",t.normalMap?"#define USE_NORMALMAP":"",t.normalMapObjectSpace?"#define USE_NORMALMAP_OBJECTSPACE":"",t.normalMapTangentSpace?"#define USE_NORMALMAP_TANGENTSPACE":"",t.emissiveMap?"#define USE_EMISSIVEMAP":"",t.anisotropy?"#define USE_ANISOTROPY":"",t.anisotropyMap?"#define USE_ANISOTROPYMAP":"",t.clearcoat?"#define USE_CLEARCOAT":"",t.clearcoatMap?"#define USE_CLEARCOATMAP":"",t.clearcoatRoughnessMap?"#define USE_CLEARCOAT_ROUGHNESSMAP":"",t.clearcoatNormalMap?"#define USE_CLEARCOAT_NORMALMAP":"",t.dispersion?"#define USE_DISPERSION":"",t.iridescence?"#define USE_IRIDESCENCE":"",t.iridescenceMap?"#define USE_IRIDESCENCEMAP":"",t.iridescenceThicknessMap?"#define USE_IRIDESCENCE_THICKNESSMAP":"",t.specularMap?"#define USE_SPECULARMAP":"",t.specularColorMap?"#define USE_SPECULAR_COLORMAP":"",t.specularIntensityMap?"#define USE_SPECULAR_INTENSITYMAP":"",t.roughnessMap?"#define USE_ROUGHNESSMAP":"",t.metalnessMap?"#define USE_METALNESSMAP":"",t.alphaMap?"#define USE_ALPHAMAP":"",t.alphaTest?"#define USE_ALPHATEST":"",t.alphaHash?"#define USE_ALPHAHASH":"",t.sheen?"#define USE_SHEEN":"",t.sheenColorMap?"#define USE_SHEEN_COLORMAP":"",t.sheenRoughnessMap?"#define USE_SHEEN_ROUGHNESSMAP":"",t.transmission?"#define USE_TRANSMISSION":"",t.transmissionMap?"#define USE_TRANSMISSIONMAP":"",t.thicknessMap?"#define USE_THICKNESSMAP":"",t.vertexTangents&&t.flatShading===!1?"#define USE_TANGENT":"",t.vertexColors||t.instancingColor||t.batchingColor?"#define USE_COLOR":"",t.vertexAlphas?"#define USE_COLOR_ALPHA":"",t.vertexUv1s?"#define USE_UV1":"",t.vertexUv2s?"#define USE_UV2":"",t.vertexUv3s?"#define USE_UV3":"",t.pointsUvs?"#define USE_POINTS_UV":"",t.gradientMap?"#define USE_GRADIENTMAP":"",t.flatShading?"#define FLAT_SHADED":"",t.doubleSided?"#define DOUBLE_SIDED":"",t.flipSided?"#define FLIP_SIDED":"",t.shadowMapEnabled?"#define USE_SHADOWMAP":"",t.shadowMapEnabled?"#define "+c:"",t.premultipliedAlpha?"#define PREMULTIPLIED_ALPHA":"",t.numLightProbes>0?"#define USE_LIGHT_PROBES":"",t.decodeVideoTexture?"#define DECODE_VIDEO_TEXTURE":"",t.decodeVideoTextureEmissive?"#define DECODE_VIDEO_TEXTURE_EMISSIVE":"",t.logarithmicDepthBuffer?"#define USE_LOGARITHMIC_DEPTH_BUFFER":"",t.reversedDepthBuffer?"#define USE_REVERSED_DEPTH_BUFFER":"","uniform mat4 viewMatrix;","uniform vec3 cameraPosition;","uniform bool isOrthographic;",t.toneMapping!==qn?"#define TONE_MAPPING":"",t.toneMapping!==qn?Ke.tonemapping_pars_fragment:"",t.toneMapping!==qn?Ux("toneMapping",t.toneMapping):"",t.dithering?"#define DITHERING":"",t.opaque?"#define OPAQUE":"",Ke.colorspace_pars_fragment,Lx("linearToOutputTexel",t.outputColorSpace),Fx(),t.useDepthPacking?"#define DEPTH_PACKING "+t.depthPacking:"",`
`].filter(Rr).join(`
`)),a=vc(a),a=sd(a,t),a=rd(a,t),o=vc(o),o=sd(o,t),o=rd(o,t),a=ad(a),o=ad(o),t.isRawShaderMaterial!==!0&&(T=`#version 300 es
`,m=[f,"#define attribute in","#define varying out","#define texture2D texture"].join(`
`)+`
`+m,p=["#define varying in",t.glslVersion===tc?"":"layout(location = 0) out highp vec4 pc_fragColor;",t.glslVersion===tc?"":"#define gl_FragColor pc_fragColor","#define gl_FragDepthEXT gl_FragDepth","#define texture2D texture","#define textureCube texture","#define texture2DProj textureProj","#define texture2DLodEXT textureLod","#define texture2DProjLodEXT textureProjLod","#define textureCubeLodEXT textureLod","#define texture2DGradEXT textureGrad","#define texture2DProjGradEXT textureProjGrad","#define textureCubeGradEXT textureGrad"].join(`
`)+`
`+p);let M=T+m+a,y=T+p+o,R=td(s,s.VERTEX_SHADER,M),E=td(s,s.FRAGMENT_SHADER,y);s.attachShader(x,R),s.attachShader(x,E),t.index0AttributeName!==void 0?s.bindAttribLocation(x,0,t.index0AttributeName):t.morphTargets===!0&&s.bindAttribLocation(x,0,"position"),s.linkProgram(x);function P(C){if(n.debug.checkShaderErrors){let k=s.getProgramInfoLog(x)||"",G=s.getShaderInfoLog(R)||"",q=s.getShaderInfoLog(E)||"",X=k.trim(),V=G.trim(),te=q.trim(),U=!0,Q=!0;if(s.getProgramParameter(x,s.LINK_STATUS)===!1)if(U=!1,typeof n.debug.onShaderError=="function")n.debug.onShaderError(s,x,R,E);else{let he=id(s,R,"vertex"),ue=id(s,E,"fragment");console.error("THREE.WebGLProgram: Shader Error "+s.getError()+" - VALIDATE_STATUS "+s.getProgramParameter(x,s.VALIDATE_STATUS)+`

Material Name: `+C.name+`
Material Type: `+C.type+`

Program Info Log: `+X+`
`+he+`
`+ue)}else X!==""?console.warn("THREE.WebGLProgram: Program Info Log:",X):(V===""||te==="")&&(Q=!1);Q&&(C.diagnostics={runnable:U,programLog:X,vertexShader:{log:V,prefix:m},fragmentShader:{log:te,prefix:p}})}s.deleteShader(R),s.deleteShader(E),D=new Ts(s,x),b=Bx(s,x)}let D;this.getUniforms=function(){return D===void 0&&P(this),D};let b;this.getAttributes=function(){return b===void 0&&P(this),b};let w=t.rendererExtensionParallelShaderCompile===!1;return this.isReady=function(){return w===!1&&(w=s.getProgramParameter(x,Px)),w},this.destroy=function(){i.releaseStatesOfProgram(this),s.deleteProgram(x),this.program=void 0},this.type=t.shaderType,this.name=t.shaderName,this.id=Ix++,this.cacheKey=e,this.usedTimes=1,this.program=x,this.vertexShader=R,this.fragmentShader=E,this}var Kx=0,yc=class{constructor(){this.shaderCache=new Map,this.materialCache=new Map}update(e){let t=e.vertexShader,i=e.fragmentShader,s=this._getShaderStage(t),r=this._getShaderStage(i),a=this._getShaderCacheForMaterial(e);return a.has(s)===!1&&(a.add(s),s.usedTimes++),a.has(r)===!1&&(a.add(r),r.usedTimes++),this}remove(e){let t=this.materialCache.get(e);for(let i of t)i.usedTimes--,i.usedTimes===0&&this.shaderCache.delete(i.code);return this.materialCache.delete(e),this}getVertexShaderID(e){return this._getShaderStage(e.vertexShader).id}getFragmentShaderID(e){return this._getShaderStage(e.fragmentShader).id}dispose(){this.shaderCache.clear(),this.materialCache.clear()}_getShaderCacheForMaterial(e){let t=this.materialCache,i=t.get(e);return i===void 0&&(i=new Set,t.set(e,i)),i}_getShaderStage(e){let t=this.shaderCache,i=t.get(e);return i===void 0&&(i=new wc(e),t.set(e,i)),i}},wc=class{constructor(e){this.id=Kx++,this.code=e,this.usedTimes=0}};function jx(n,e,t,i,s,r,a){let o=new Ks,c=new yc,l=new Set,u=[],h=s.logarithmicDepthBuffer,d=s.vertexTextures,f=s.precision,g={MeshDepthMaterial:"depth",MeshDistanceMaterial:"distanceRGBA",MeshNormalMaterial:"normal",MeshBasicMaterial:"basic",MeshLambertMaterial:"lambert",MeshPhongMaterial:"phong",MeshToonMaterial:"toon",MeshStandardMaterial:"physical",MeshPhysicalMaterial:"physical",MeshMatcapMaterial:"matcap",LineBasicMaterial:"basic",LineDashedMaterial:"dashed",PointsMaterial:"points",ShadowMaterial:"shadow",SpriteMaterial:"sprite"};function x(b){return l.add(b),b===0?"uv":`uv${b}`}function m(b,w,C,k,G){let q=k.fog,X=G.geometry,V=b.isMeshStandardMaterial?k.environment:null,te=(b.isMeshStandardMaterial?t:e).get(b.envMap||V),U=te&&te.mapping===Mr?te.image.height:null,Q=g[b.type];b.precision!==null&&(f=s.getMaxPrecision(b.precision),f!==b.precision&&console.warn("THREE.WebGLProgram.getParameters:",b.precision,"not supported, using",f,"instead."));let he=X.morphAttributes.position||X.morphAttributes.normal||X.morphAttributes.color,ue=he!==void 0?he.length:0,ze=0;X.morphAttributes.position!==void 0&&(ze=1),X.morphAttributes.normal!==void 0&&(ze=2),X.morphAttributes.color!==void 0&&(ze=3);let je,Qe,it,Y;if(Q){let at=Rn[Q];je=at.vertexShader,Qe=at.fragmentShader}else je=b.vertexShader,Qe=b.fragmentShader,c.update(b),it=c.getVertexShaderID(b),Y=c.getFragmentShaderID(b);let se=n.getRenderTarget(),Me=n.state.buffers.depth.getReversed(),Ue=G.isInstancedMesh===!0,Ae=G.isBatchedMesh===!0,et=!!b.map,ft=!!b.matcap,A=!!te,ne=!!b.aoMap,J=!!b.lightMap,Z=!!b.bumpMap,$=!!b.normalMap,pe=!!b.displacementMap,re=!!b.emissiveMap,me=!!b.metalnessMap,We=!!b.roughnessMap,He=b.anisotropy>0,S=b.clearcoat>0,_=b.dispersion>0,O=b.iridescence>0,H=b.sheen>0,ee=b.transmission>0,W=He&&!!b.anisotropyMap,Ne=S&&!!b.clearcoatMap,fe=S&&!!b.clearcoatNormalMap,Ce=S&&!!b.clearcoatRoughnessMap,Re=O&&!!b.iridescenceMap,ae=O&&!!b.iridescenceThicknessMap,we=H&&!!b.sheenColorMap,Be=H&&!!b.sheenRoughnessMap,Le=!!b.specularMap,ve=!!b.specularColorMap,Ze=!!b.specularIntensityMap,I=ee&&!!b.transmissionMap,ce=ee&&!!b.thicknessMap,ge=!!b.gradientMap,Se=!!b.alphaMap,oe=b.alphaTest>0,K=!!b.alphaHash,Pe=!!b.extensions,Xe=qn;b.toneMapped&&(se===null||se.isXRRenderTarget===!0)&&(Xe=n.toneMapping);let pt={shaderID:Q,shaderType:b.type,shaderName:b.name,vertexShader:je,fragmentShader:Qe,defines:b.defines,customVertexShaderID:it,customFragmentShaderID:Y,isRawShaderMaterial:b.isRawShaderMaterial===!0,glslVersion:b.glslVersion,precision:f,batching:Ae,batchingColor:Ae&&G._colorsTexture!==null,instancing:Ue,instancingColor:Ue&&G.instanceColor!==null,instancingMorph:Ue&&G.morphTexture!==null,supportsVertexTextures:d,outputColorSpace:se===null?n.outputColorSpace:se.isXRRenderTarget===!0?se.texture.colorSpace:Ri,alphaToCoverage:!!b.alphaToCoverage,map:et,matcap:ft,envMap:A,envMapMode:A&&te.mapping,envMapCubeUVHeight:U,aoMap:ne,lightMap:J,bumpMap:Z,normalMap:$,displacementMap:d&&pe,emissiveMap:re,normalMapObjectSpace:$&&b.normalMapType===Tu,normalMapTangentSpace:$&&b.normalMapType===Ql,metalnessMap:me,roughnessMap:We,anisotropy:He,anisotropyMap:W,clearcoat:S,clearcoatMap:Ne,clearcoatNormalMap:fe,clearcoatRoughnessMap:Ce,dispersion:_,iridescence:O,iridescenceMap:Re,iridescenceThicknessMap:ae,sheen:H,sheenColorMap:we,sheenRoughnessMap:Be,specularMap:Le,specularColorMap:ve,specularIntensityMap:Ze,transmission:ee,transmissionMap:I,thicknessMap:ce,gradientMap:ge,opaque:b.transparent===!1&&b.blending===Ai&&b.alphaToCoverage===!1,alphaMap:Se,alphaTest:oe,alphaHash:K,combine:b.combine,mapUv:et&&x(b.map.channel),aoMapUv:ne&&x(b.aoMap.channel),lightMapUv:J&&x(b.lightMap.channel),bumpMapUv:Z&&x(b.bumpMap.channel),normalMapUv:$&&x(b.normalMap.channel),displacementMapUv:pe&&x(b.displacementMap.channel),emissiveMapUv:re&&x(b.emissiveMap.channel),metalnessMapUv:me&&x(b.metalnessMap.channel),roughnessMapUv:We&&x(b.roughnessMap.channel),anisotropyMapUv:W&&x(b.anisotropyMap.channel),clearcoatMapUv:Ne&&x(b.clearcoatMap.channel),clearcoatNormalMapUv:fe&&x(b.clearcoatNormalMap.channel),clearcoatRoughnessMapUv:Ce&&x(b.clearcoatRoughnessMap.channel),iridescenceMapUv:Re&&x(b.iridescenceMap.channel),iridescenceThicknessMapUv:ae&&x(b.iridescenceThicknessMap.channel),sheenColorMapUv:we&&x(b.sheenColorMap.channel),sheenRoughnessMapUv:Be&&x(b.sheenRoughnessMap.channel),specularMapUv:Le&&x(b.specularMap.channel),specularColorMapUv:ve&&x(b.specularColorMap.channel),specularIntensityMapUv:Ze&&x(b.specularIntensityMap.channel),transmissionMapUv:I&&x(b.transmissionMap.channel),thicknessMapUv:ce&&x(b.thicknessMap.channel),alphaMapUv:Se&&x(b.alphaMap.channel),vertexTangents:!!X.attributes.tangent&&($||He),vertexColors:b.vertexColors,vertexAlphas:b.vertexColors===!0&&!!X.attributes.color&&X.attributes.color.itemSize===4,pointsUvs:G.isPoints===!0&&!!X.attributes.uv&&(et||Se),fog:!!q,useFog:b.fog===!0,fogExp2:!!q&&q.isFogExp2,flatShading:b.flatShading===!0&&b.wireframe===!1,sizeAttenuation:b.sizeAttenuation===!0,logarithmicDepthBuffer:h,reversedDepthBuffer:Me,skinning:G.isSkinnedMesh===!0,morphTargets:X.morphAttributes.position!==void 0,morphNormals:X.morphAttributes.normal!==void 0,morphColors:X.morphAttributes.color!==void 0,morphTargetsCount:ue,morphTextureStride:ze,numDirLights:w.directional.length,numPointLights:w.point.length,numSpotLights:w.spot.length,numSpotLightMaps:w.spotLightMap.length,numRectAreaLights:w.rectArea.length,numHemiLights:w.hemi.length,numDirLightShadows:w.directionalShadowMap.length,numPointLightShadows:w.pointShadowMap.length,numSpotLightShadows:w.spotShadowMap.length,numSpotLightShadowsWithMaps:w.numSpotLightShadowsWithMaps,numLightProbes:w.numLightProbes,numClippingPlanes:a.numPlanes,numClipIntersection:a.numIntersection,dithering:b.dithering,shadowMapEnabled:n.shadowMap.enabled&&C.length>0,shadowMapType:n.shadowMap.type,toneMapping:Xe,decodeVideoTexture:et&&b.map.isVideoTexture===!0&&st.getTransfer(b.map.colorSpace)===ot,decodeVideoTextureEmissive:re&&b.emissiveMap.isVideoTexture===!0&&st.getTransfer(b.emissiveMap.colorSpace)===ot,premultipliedAlpha:b.premultipliedAlpha,doubleSided:b.side===An,flipSided:b.side===Wt,useDepthPacking:b.depthPacking>=0,depthPacking:b.depthPacking||0,index0AttributeName:b.index0AttributeName,extensionClipCullDistance:Pe&&b.extensions.clipCullDistance===!0&&i.has("WEBGL_clip_cull_distance"),extensionMultiDraw:(Pe&&b.extensions.multiDraw===!0||Ae)&&i.has("WEBGL_multi_draw"),rendererExtensionParallelShaderCompile:i.has("KHR_parallel_shader_compile"),customProgramCacheKey:b.customProgramCacheKey()};return pt.vertexUv1s=l.has(1),pt.vertexUv2s=l.has(2),pt.vertexUv3s=l.has(3),l.clear(),pt}function p(b){let w=[];if(b.shaderID?w.push(b.shaderID):(w.push(b.customVertexShaderID),w.push(b.customFragmentShaderID)),b.defines!==void 0)for(let C in b.defines)w.push(C),w.push(b.defines[C]);return b.isRawShaderMaterial===!1&&(T(w,b),M(w,b),w.push(n.outputColorSpace)),w.push(b.customProgramCacheKey),w.join()}function T(b,w){b.push(w.precision),b.push(w.outputColorSpace),b.push(w.envMapMode),b.push(w.envMapCubeUVHeight),b.push(w.mapUv),b.push(w.alphaMapUv),b.push(w.lightMapUv),b.push(w.aoMapUv),b.push(w.bumpMapUv),b.push(w.normalMapUv),b.push(w.displacementMapUv),b.push(w.emissiveMapUv),b.push(w.metalnessMapUv),b.push(w.roughnessMapUv),b.push(w.anisotropyMapUv),b.push(w.clearcoatMapUv),b.push(w.clearcoatNormalMapUv),b.push(w.clearcoatRoughnessMapUv),b.push(w.iridescenceMapUv),b.push(w.iridescenceThicknessMapUv),b.push(w.sheenColorMapUv),b.push(w.sheenRoughnessMapUv),b.push(w.specularMapUv),b.push(w.specularColorMapUv),b.push(w.specularIntensityMapUv),b.push(w.transmissionMapUv),b.push(w.thicknessMapUv),b.push(w.combine),b.push(w.fogExp2),b.push(w.sizeAttenuation),b.push(w.morphTargetsCount),b.push(w.morphAttributeCount),b.push(w.numDirLights),b.push(w.numPointLights),b.push(w.numSpotLights),b.push(w.numSpotLightMaps),b.push(w.numHemiLights),b.push(w.numRectAreaLights),b.push(w.numDirLightShadows),b.push(w.numPointLightShadows),b.push(w.numSpotLightShadows),b.push(w.numSpotLightShadowsWithMaps),b.push(w.numLightProbes),b.push(w.shadowMapType),b.push(w.toneMapping),b.push(w.numClippingPlanes),b.push(w.numClipIntersection),b.push(w.depthPacking)}function M(b,w){o.disableAll(),w.supportsVertexTextures&&o.enable(0),w.instancing&&o.enable(1),w.instancingColor&&o.enable(2),w.instancingMorph&&o.enable(3),w.matcap&&o.enable(4),w.envMap&&o.enable(5),w.normalMapObjectSpace&&o.enable(6),w.normalMapTangentSpace&&o.enable(7),w.clearcoat&&o.enable(8),w.iridescence&&o.enable(9),w.alphaTest&&o.enable(10),w.vertexColors&&o.enable(11),w.vertexAlphas&&o.enable(12),w.vertexUv1s&&o.enable(13),w.vertexUv2s&&o.enable(14),w.vertexUv3s&&o.enable(15),w.vertexTangents&&o.enable(16),w.anisotropy&&o.enable(17),w.alphaHash&&o.enable(18),w.batching&&o.enable(19),w.dispersion&&o.enable(20),w.batchingColor&&o.enable(21),w.gradientMap&&o.enable(22),b.push(o.mask),o.disableAll(),w.fog&&o.enable(0),w.useFog&&o.enable(1),w.flatShading&&o.enable(2),w.logarithmicDepthBuffer&&o.enable(3),w.reversedDepthBuffer&&o.enable(4),w.skinning&&o.enable(5),w.morphTargets&&o.enable(6),w.morphNormals&&o.enable(7),w.morphColors&&o.enable(8),w.premultipliedAlpha&&o.enable(9),w.shadowMapEnabled&&o.enable(10),w.doubleSided&&o.enable(11),w.flipSided&&o.enable(12),w.useDepthPacking&&o.enable(13),w.dithering&&o.enable(14),w.transmission&&o.enable(15),w.sheen&&o.enable(16),w.opaque&&o.enable(17),w.pointsUvs&&o.enable(18),w.decodeVideoTexture&&o.enable(19),w.decodeVideoTextureEmissive&&o.enable(20),w.alphaToCoverage&&o.enable(21),b.push(o.mask)}function y(b){let w=g[b.type],C;if(w){let k=Rn[w];C=Fu.clone(k.uniforms)}else C=b.uniforms;return C}function R(b,w){let C;for(let k=0,G=u.length;k<G;k++){let q=u[k];if(q.cacheKey===w){C=q,++C.usedTimes;break}}return C===void 0&&(C=new Jx(n,w,b,r),u.push(C)),C}function E(b){if(--b.usedTimes===0){let w=u.indexOf(b);u[w]=u[u.length-1],u.pop(),b.destroy()}}function P(b){c.remove(b)}function D(){c.dispose()}return{getParameters:m,getProgramCacheKey:p,getUniforms:y,acquireProgram:R,releaseProgram:E,releaseShaderCache:P,programs:u,dispose:D}}function Qx(){let n=new WeakMap;function e(a){return n.has(a)}function t(a){let o=n.get(a);return o===void 0&&(o={},n.set(a,o)),o}function i(a){n.delete(a)}function s(a,o,c){n.get(a)[o]=c}function r(){n=new WeakMap}return{has:e,get:t,remove:i,update:s,dispose:r}}function e0(n,e){return n.groupOrder!==e.groupOrder?n.groupOrder-e.groupOrder:n.renderOrder!==e.renderOrder?n.renderOrder-e.renderOrder:n.material.id!==e.material.id?n.material.id-e.material.id:n.z!==e.z?n.z-e.z:n.id-e.id}function ld(n,e){return n.groupOrder!==e.groupOrder?n.groupOrder-e.groupOrder:n.renderOrder!==e.renderOrder?n.renderOrder-e.renderOrder:n.z!==e.z?e.z-n.z:n.id-e.id}function cd(){let n=[],e=0,t=[],i=[],s=[];function r(){e=0,t.length=0,i.length=0,s.length=0}function a(h,d,f,g,x,m){let p=n[e];return p===void 0?(p={id:h.id,object:h,geometry:d,material:f,groupOrder:g,renderOrder:h.renderOrder,z:x,group:m},n[e]=p):(p.id=h.id,p.object=h,p.geometry=d,p.material=f,p.groupOrder=g,p.renderOrder=h.renderOrder,p.z=x,p.group=m),e++,p}function o(h,d,f,g,x,m){let p=a(h,d,f,g,x,m);f.transmission>0?i.push(p):f.transparent===!0?s.push(p):t.push(p)}function c(h,d,f,g,x,m){let p=a(h,d,f,g,x,m);f.transmission>0?i.unshift(p):f.transparent===!0?s.unshift(p):t.unshift(p)}function l(h,d){t.length>1&&t.sort(h||e0),i.length>1&&i.sort(d||ld),s.length>1&&s.sort(d||ld)}function u(){for(let h=e,d=n.length;h<d;h++){let f=n[h];if(f.id===null)break;f.id=null,f.object=null,f.geometry=null,f.material=null,f.group=null}}return{opaque:t,transmissive:i,transparent:s,init:r,push:o,unshift:c,finish:u,sort:l}}function t0(){let n=new WeakMap;function e(i,s){let r=n.get(i),a;return r===void 0?(a=new cd,n.set(i,[a])):s>=r.length?(a=new cd,r.push(a)):a=r[s],a}function t(){n=new WeakMap}return{get:e,dispose:t}}function n0(){let n={};return{get:function(e){if(n[e.id]!==void 0)return n[e.id];let t;switch(e.type){case"DirectionalLight":t={direction:new N,color:new qe};break;case"SpotLight":t={position:new N,direction:new N,color:new qe,distance:0,coneCos:0,penumbraCos:0,decay:0};break;case"PointLight":t={position:new N,color:new qe,distance:0,decay:0};break;case"HemisphereLight":t={direction:new N,skyColor:new qe,groundColor:new qe};break;case"RectAreaLight":t={color:new qe,position:new N,halfWidth:new N,halfHeight:new N};break}return n[e.id]=t,t}}}function i0(){let n={};return{get:function(e){if(n[e.id]!==void 0)return n[e.id];let t;switch(e.type){case"DirectionalLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new de};break;case"SpotLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new de};break;case"PointLight":t={shadowIntensity:1,shadowBias:0,shadowNormalBias:0,shadowRadius:1,shadowMapSize:new de,shadowCameraNear:1,shadowCameraFar:1e3};break}return n[e.id]=t,t}}}var s0=0;function r0(n,e){return(e.castShadow?2:0)-(n.castShadow?2:0)+(e.map?1:0)-(n.map?1:0)}function a0(n){let e=new n0,t=i0(),i={version:0,hash:{directionalLength:-1,pointLength:-1,spotLength:-1,rectAreaLength:-1,hemiLength:-1,numDirectionalShadows:-1,numPointShadows:-1,numSpotShadows:-1,numSpotMaps:-1,numLightProbes:-1},ambient:[0,0,0],probe:[],directional:[],directionalShadow:[],directionalShadowMap:[],directionalShadowMatrix:[],spot:[],spotLightMap:[],spotShadow:[],spotShadowMap:[],spotLightMatrix:[],rectArea:[],rectAreaLTC1:null,rectAreaLTC2:null,point:[],pointShadow:[],pointShadowMap:[],pointShadowMatrix:[],hemi:[],numSpotLightShadowsWithMaps:0,numLightProbes:0};for(let l=0;l<9;l++)i.probe.push(new N);let s=new N,r=new Mt,a=new Mt;function o(l){let u=0,h=0,d=0;for(let b=0;b<9;b++)i.probe[b].set(0,0,0);let f=0,g=0,x=0,m=0,p=0,T=0,M=0,y=0,R=0,E=0,P=0;l.sort(r0);for(let b=0,w=l.length;b<w;b++){let C=l[b],k=C.color,G=C.intensity,q=C.distance,X=C.shadow&&C.shadow.map?C.shadow.map.texture:null;if(C.isAmbientLight)u+=k.r*G,h+=k.g*G,d+=k.b*G;else if(C.isLightProbe){for(let V=0;V<9;V++)i.probe[V].addScaledVector(C.sh.coefficients[V],G);P++}else if(C.isDirectionalLight){let V=e.get(C);if(V.color.copy(C.color).multiplyScalar(C.intensity),C.castShadow){let te=C.shadow,U=t.get(C);U.shadowIntensity=te.intensity,U.shadowBias=te.bias,U.shadowNormalBias=te.normalBias,U.shadowRadius=te.radius,U.shadowMapSize=te.mapSize,i.directionalShadow[f]=U,i.directionalShadowMap[f]=X,i.directionalShadowMatrix[f]=C.shadow.matrix,T++}i.directional[f]=V,f++}else if(C.isSpotLight){let V=e.get(C);V.position.setFromMatrixPosition(C.matrixWorld),V.color.copy(k).multiplyScalar(G),V.distance=q,V.coneCos=Math.cos(C.angle),V.penumbraCos=Math.cos(C.angle*(1-C.penumbra)),V.decay=C.decay,i.spot[x]=V;let te=C.shadow;if(C.map&&(i.spotLightMap[R]=C.map,R++,te.updateMatrices(C),C.castShadow&&E++),i.spotLightMatrix[x]=te.matrix,C.castShadow){let U=t.get(C);U.shadowIntensity=te.intensity,U.shadowBias=te.bias,U.shadowNormalBias=te.normalBias,U.shadowRadius=te.radius,U.shadowMapSize=te.mapSize,i.spotShadow[x]=U,i.spotShadowMap[x]=X,y++}x++}else if(C.isRectAreaLight){let V=e.get(C);V.color.copy(k).multiplyScalar(G),V.halfWidth.set(C.width*.5,0,0),V.halfHeight.set(0,C.height*.5,0),i.rectArea[m]=V,m++}else if(C.isPointLight){let V=e.get(C);if(V.color.copy(C.color).multiplyScalar(C.intensity),V.distance=C.distance,V.decay=C.decay,C.castShadow){let te=C.shadow,U=t.get(C);U.shadowIntensity=te.intensity,U.shadowBias=te.bias,U.shadowNormalBias=te.normalBias,U.shadowRadius=te.radius,U.shadowMapSize=te.mapSize,U.shadowCameraNear=te.camera.near,U.shadowCameraFar=te.camera.far,i.pointShadow[g]=U,i.pointShadowMap[g]=X,i.pointShadowMatrix[g]=C.shadow.matrix,M++}i.point[g]=V,g++}else if(C.isHemisphereLight){let V=e.get(C);V.skyColor.copy(C.color).multiplyScalar(G),V.groundColor.copy(C.groundColor).multiplyScalar(G),i.hemi[p]=V,p++}}m>0&&(n.has("OES_texture_float_linear")===!0?(i.rectAreaLTC1=xe.LTC_FLOAT_1,i.rectAreaLTC2=xe.LTC_FLOAT_2):(i.rectAreaLTC1=xe.LTC_HALF_1,i.rectAreaLTC2=xe.LTC_HALF_2)),i.ambient[0]=u,i.ambient[1]=h,i.ambient[2]=d;let D=i.hash;(D.directionalLength!==f||D.pointLength!==g||D.spotLength!==x||D.rectAreaLength!==m||D.hemiLength!==p||D.numDirectionalShadows!==T||D.numPointShadows!==M||D.numSpotShadows!==y||D.numSpotMaps!==R||D.numLightProbes!==P)&&(i.directional.length=f,i.spot.length=x,i.rectArea.length=m,i.point.length=g,i.hemi.length=p,i.directionalShadow.length=T,i.directionalShadowMap.length=T,i.pointShadow.length=M,i.pointShadowMap.length=M,i.spotShadow.length=y,i.spotShadowMap.length=y,i.directionalShadowMatrix.length=T,i.pointShadowMatrix.length=M,i.spotLightMatrix.length=y+R-E,i.spotLightMap.length=R,i.numSpotLightShadowsWithMaps=E,i.numLightProbes=P,D.directionalLength=f,D.pointLength=g,D.spotLength=x,D.rectAreaLength=m,D.hemiLength=p,D.numDirectionalShadows=T,D.numPointShadows=M,D.numSpotShadows=y,D.numSpotMaps=R,D.numLightProbes=P,i.version=s0++)}function c(l,u){let h=0,d=0,f=0,g=0,x=0,m=u.matrixWorldInverse;for(let p=0,T=l.length;p<T;p++){let M=l[p];if(M.isDirectionalLight){let y=i.directional[h];y.direction.setFromMatrixPosition(M.matrixWorld),s.setFromMatrixPosition(M.target.matrixWorld),y.direction.sub(s),y.direction.transformDirection(m),h++}else if(M.isSpotLight){let y=i.spot[f];y.position.setFromMatrixPosition(M.matrixWorld),y.position.applyMatrix4(m),y.direction.setFromMatrixPosition(M.matrixWorld),s.setFromMatrixPosition(M.target.matrixWorld),y.direction.sub(s),y.direction.transformDirection(m),f++}else if(M.isRectAreaLight){let y=i.rectArea[g];y.position.setFromMatrixPosition(M.matrixWorld),y.position.applyMatrix4(m),a.identity(),r.copy(M.matrixWorld),r.premultiply(m),a.extractRotation(r),y.halfWidth.set(M.width*.5,0,0),y.halfHeight.set(0,M.height*.5,0),y.halfWidth.applyMatrix4(a),y.halfHeight.applyMatrix4(a),g++}else if(M.isPointLight){let y=i.point[d];y.position.setFromMatrixPosition(M.matrixWorld),y.position.applyMatrix4(m),d++}else if(M.isHemisphereLight){let y=i.hemi[x];y.direction.setFromMatrixPosition(M.matrixWorld),y.direction.transformDirection(m),x++}}}return{setup:o,setupView:c,state:i}}function hd(n){let e=new a0(n),t=[],i=[];function s(u){l.camera=u,t.length=0,i.length=0}function r(u){t.push(u)}function a(u){i.push(u)}function o(){e.setup(t)}function c(u){e.setupView(t,u)}let l={lightsArray:t,shadowsArray:i,camera:null,lights:e,transmissionRenderTarget:{}};return{init:s,state:l,setupLights:o,setupLightsView:c,pushLight:r,pushShadow:a}}function o0(n){let e=new WeakMap;function t(s,r=0){let a=e.get(s),o;return a===void 0?(o=new hd(n),e.set(s,[o])):r>=a.length?(o=new hd(n),a.push(o)):o=a[r],o}function i(){e=new WeakMap}return{get:t,dispose:i}}var l0=`void main() {
	gl_Position = vec4( position, 1.0 );
}`,c0=`uniform sampler2D shadow_pass;
uniform vec2 resolution;
uniform float radius;
#include <packing>
void main() {
	const float samples = float( VSM_SAMPLES );
	float mean = 0.0;
	float squared_mean = 0.0;
	float uvStride = samples <= 1.0 ? 0.0 : 2.0 / ( samples - 1.0 );
	float uvStart = samples <= 1.0 ? 0.0 : - 1.0;
	for ( float i = 0.0; i < samples; i ++ ) {
		float uvOffset = uvStart + i * uvStride;
		#ifdef HORIZONTAL_PASS
			vec2 distribution = unpackRGBATo2Half( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( uvOffset, 0.0 ) * radius ) / resolution ) );
			mean += distribution.x;
			squared_mean += distribution.y * distribution.y + distribution.x * distribution.x;
		#else
			float depth = unpackRGBAToDepth( texture2D( shadow_pass, ( gl_FragCoord.xy + vec2( 0.0, uvOffset ) * radius ) / resolution ) );
			mean += depth;
			squared_mean += depth * depth;
		#endif
	}
	mean = mean / samples;
	squared_mean = squared_mean / samples;
	float std_dev = sqrt( squared_mean - mean * mean );
	gl_FragColor = pack2HalfToRGBA( vec2( mean, std_dev ) );
}`;function h0(n,e,t){let i=new ms,s=new de,r=new de,a=new wt,o=new Aa({depthPacking:Su}),c=new Ca,l={},u=t.maxTextureSize,h={[Wn]:Wt,[Wt]:Wn,[An]:An},d=new xn({defines:{VSM_SAMPLES:8},uniforms:{shadow_pass:{value:null},resolution:{value:new de},radius:{value:4}},vertexShader:l0,fragmentShader:c0}),f=d.clone();f.defines.HORIZONTAL_PASS=1;let g=new cn;g.setAttribute("position",new Nt(new Float32Array([-1,-1,.5,3,-1,.5,-1,3,.5]),3));let x=new Ot(g,d),m=this;this.enabled=!1,this.autoUpdate=!0,this.needsUpdate=!1,this.type=Bl;let p=this.type;this.render=function(E,P,D){if(m.enabled===!1||m.autoUpdate===!1&&m.needsUpdate===!1||E.length===0)return;let b=n.getRenderTarget(),w=n.getActiveCubeFace(),C=n.getActiveMipmapLevel(),k=n.state;k.setBlending(Xn),k.buffers.depth.getReversed()===!0?k.buffers.color.setClear(0,0,0,0):k.buffers.color.setClear(1,1,1,1),k.buffers.depth.setTest(!0),k.setScissorTest(!1);let G=p!==En&&this.type===En,q=p===En&&this.type!==En;for(let X=0,V=E.length;X<V;X++){let te=E[X],U=te.shadow;if(U===void 0){console.warn("THREE.WebGLShadowMap:",te,"has no shadow.");continue}if(U.autoUpdate===!1&&U.needsUpdate===!1)continue;s.copy(U.mapSize);let Q=U.getFrameExtents();if(s.multiply(Q),r.copy(U.mapSize),(s.x>u||s.y>u)&&(s.x>u&&(r.x=Math.floor(u/Q.x),s.x=r.x*Q.x,U.mapSize.x=r.x),s.y>u&&(r.y=Math.floor(u/Q.y),s.y=r.y*Q.y,U.mapSize.y=r.y)),U.map===null||G===!0||q===!0){let ue=this.type!==En?{minFilter:on,magFilter:on}:{};U.map!==null&&U.map.dispose(),U.map=new Sn(s.x,s.y,ue),U.map.texture.name=te.name+".shadowMap",U.camera.updateProjectionMatrix()}n.setRenderTarget(U.map),n.clear();let he=U.getViewportCount();for(let ue=0;ue<he;ue++){let ze=U.getViewport(ue);a.set(r.x*ze.x,r.y*ze.y,r.x*ze.z,r.y*ze.w),k.viewport(a),U.updateMatrices(te,ue),i=U.getFrustum(),y(P,D,U.camera,te,this.type)}U.isPointLightShadow!==!0&&this.type===En&&T(U,D),U.needsUpdate=!1}p=this.type,m.needsUpdate=!1,n.setRenderTarget(b,w,C)};function T(E,P){let D=e.update(x);d.defines.VSM_SAMPLES!==E.blurSamples&&(d.defines.VSM_SAMPLES=E.blurSamples,f.defines.VSM_SAMPLES=E.blurSamples,d.needsUpdate=!0,f.needsUpdate=!0),E.mapPass===null&&(E.mapPass=new Sn(s.x,s.y)),d.uniforms.shadow_pass.value=E.map.texture,d.uniforms.resolution.value=E.mapSize,d.uniforms.radius.value=E.radius,n.setRenderTarget(E.mapPass),n.clear(),n.renderBufferDirect(P,null,D,d,x,null),f.uniforms.shadow_pass.value=E.mapPass.texture,f.uniforms.resolution.value=E.mapSize,f.uniforms.radius.value=E.radius,n.setRenderTarget(E.map),n.clear(),n.renderBufferDirect(P,null,D,f,x,null)}function M(E,P,D,b){let w=null,C=D.isPointLight===!0?E.customDistanceMaterial:E.customDepthMaterial;if(C!==void 0)w=C;else if(w=D.isPointLight===!0?c:o,n.localClippingEnabled&&P.clipShadows===!0&&Array.isArray(P.clippingPlanes)&&P.clippingPlanes.length!==0||P.displacementMap&&P.displacementScale!==0||P.alphaMap&&P.alphaTest>0||P.map&&P.alphaTest>0||P.alphaToCoverage===!0){let k=w.uuid,G=P.uuid,q=l[k];q===void 0&&(q={},l[k]=q);let X=q[G];X===void 0&&(X=w.clone(),q[G]=X,P.addEventListener("dispose",R)),w=X}if(w.visible=P.visible,w.wireframe=P.wireframe,b===En?w.side=P.shadowSide!==null?P.shadowSide:P.side:w.side=P.shadowSide!==null?P.shadowSide:h[P.side],w.alphaMap=P.alphaMap,w.alphaTest=P.alphaToCoverage===!0?.5:P.alphaTest,w.map=P.map,w.clipShadows=P.clipShadows,w.clippingPlanes=P.clippingPlanes,w.clipIntersection=P.clipIntersection,w.displacementMap=P.displacementMap,w.displacementScale=P.displacementScale,w.displacementBias=P.displacementBias,w.wireframeLinewidth=P.wireframeLinewidth,w.linewidth=P.linewidth,D.isPointLight===!0&&w.isMeshDistanceMaterial===!0){let k=n.properties.get(w);k.light=D}return w}function y(E,P,D,b,w){if(E.visible===!1)return;if(E.layers.test(P.layers)&&(E.isMesh||E.isLine||E.isPoints)&&(E.castShadow||E.receiveShadow&&w===En)&&(!E.frustumCulled||i.intersectsObject(E))){E.modelViewMatrix.multiplyMatrices(D.matrixWorldInverse,E.matrixWorld);let G=e.update(E),q=E.material;if(Array.isArray(q)){let X=G.groups;for(let V=0,te=X.length;V<te;V++){let U=X[V],Q=q[U.materialIndex];if(Q&&Q.visible){let he=M(E,Q,b,w);E.onBeforeShadow(n,E,P,D,G,he,U),n.renderBufferDirect(D,null,G,he,E,U),E.onAfterShadow(n,E,P,D,G,he,U)}}}else if(q.visible){let X=M(E,q,b,w);E.onBeforeShadow(n,E,P,D,G,X,null),n.renderBufferDirect(D,null,G,X,E,null),E.onAfterShadow(n,E,P,D,G,X,null)}}let k=E.children;for(let G=0,q=k.length;G<q;G++)y(k[G],P,D,b,w)}function R(E){E.target.removeEventListener("dispose",R);for(let D in l){let b=l[D],w=E.target.uuid;w in b&&(b[w].dispose(),delete b[w])}}}var u0={[Ba]:za,[Va]:Wa,[Ha]:Xa,[Ci]:Ga,[za]:Ba,[Wa]:Va,[Xa]:Ha,[Ga]:Ci};function d0(n,e){function t(){let I=!1,ce=new wt,ge=null,Se=new wt(0,0,0,0);return{setMask:function(oe){ge!==oe&&!I&&(n.colorMask(oe,oe,oe,oe),ge=oe)},setLocked:function(oe){I=oe},setClear:function(oe,K,Pe,Xe,pt){pt===!0&&(oe*=Xe,K*=Xe,Pe*=Xe),ce.set(oe,K,Pe,Xe),Se.equals(ce)===!1&&(n.clearColor(oe,K,Pe,Xe),Se.copy(ce))},reset:function(){I=!1,ge=null,Se.set(-1,0,0,0)}}}function i(){let I=!1,ce=!1,ge=null,Se=null,oe=null;return{setReversed:function(K){if(ce!==K){let Pe=e.get("EXT_clip_control");K?Pe.clipControlEXT(Pe.LOWER_LEFT_EXT,Pe.ZERO_TO_ONE_EXT):Pe.clipControlEXT(Pe.LOWER_LEFT_EXT,Pe.NEGATIVE_ONE_TO_ONE_EXT),ce=K;let Xe=oe;oe=null,this.setClear(Xe)}},getReversed:function(){return ce},setTest:function(K){K?se(n.DEPTH_TEST):Me(n.DEPTH_TEST)},setMask:function(K){ge!==K&&!I&&(n.depthMask(K),ge=K)},setFunc:function(K){if(ce&&(K=u0[K]),Se!==K){switch(K){case Ba:n.depthFunc(n.NEVER);break;case za:n.depthFunc(n.ALWAYS);break;case Va:n.depthFunc(n.LESS);break;case Ci:n.depthFunc(n.LEQUAL);break;case Ha:n.depthFunc(n.EQUAL);break;case Ga:n.depthFunc(n.GEQUAL);break;case Wa:n.depthFunc(n.GREATER);break;case Xa:n.depthFunc(n.NOTEQUAL);break;default:n.depthFunc(n.LEQUAL)}Se=K}},setLocked:function(K){I=K},setClear:function(K){oe!==K&&(ce&&(K=1-K),n.clearDepth(K),oe=K)},reset:function(){I=!1,ge=null,Se=null,oe=null,ce=!1}}}function s(){let I=!1,ce=null,ge=null,Se=null,oe=null,K=null,Pe=null,Xe=null,pt=null;return{setTest:function(at){I||(at?se(n.STENCIL_TEST):Me(n.STENCIL_TEST))},setMask:function(at){ce!==at&&!I&&(n.stencilMask(at),ce=at)},setFunc:function(at,In,wn){(ge!==at||Se!==In||oe!==wn)&&(n.stencilFunc(at,In,wn),ge=at,Se=In,oe=wn)},setOp:function(at,In,wn){(K!==at||Pe!==In||Xe!==wn)&&(n.stencilOp(at,In,wn),K=at,Pe=In,Xe=wn)},setLocked:function(at){I=at},setClear:function(at){pt!==at&&(n.clearStencil(at),pt=at)},reset:function(){I=!1,ce=null,ge=null,Se=null,oe=null,K=null,Pe=null,Xe=null,pt=null}}}let r=new t,a=new i,o=new s,c=new WeakMap,l=new WeakMap,u={},h={},d=new WeakMap,f=[],g=null,x=!1,m=null,p=null,T=null,M=null,y=null,R=null,E=null,P=new qe(0,0,0),D=0,b=!1,w=null,C=null,k=null,G=null,q=null,X=n.getParameter(n.MAX_COMBINED_TEXTURE_IMAGE_UNITS),V=!1,te=0,U=n.getParameter(n.VERSION);U.indexOf("WebGL")!==-1?(te=parseFloat(/^WebGL (\d)/.exec(U)[1]),V=te>=1):U.indexOf("OpenGL ES")!==-1&&(te=parseFloat(/^OpenGL ES (\d)/.exec(U)[1]),V=te>=2);let Q=null,he={},ue=n.getParameter(n.SCISSOR_BOX),ze=n.getParameter(n.VIEWPORT),je=new wt().fromArray(ue),Qe=new wt().fromArray(ze);function it(I,ce,ge,Se){let oe=new Uint8Array(4),K=n.createTexture();n.bindTexture(I,K),n.texParameteri(I,n.TEXTURE_MIN_FILTER,n.NEAREST),n.texParameteri(I,n.TEXTURE_MAG_FILTER,n.NEAREST);for(let Pe=0;Pe<ge;Pe++)I===n.TEXTURE_3D||I===n.TEXTURE_2D_ARRAY?n.texImage3D(ce,0,n.RGBA,1,1,Se,0,n.RGBA,n.UNSIGNED_BYTE,oe):n.texImage2D(ce+Pe,0,n.RGBA,1,1,0,n.RGBA,n.UNSIGNED_BYTE,oe);return K}let Y={};Y[n.TEXTURE_2D]=it(n.TEXTURE_2D,n.TEXTURE_2D,1),Y[n.TEXTURE_CUBE_MAP]=it(n.TEXTURE_CUBE_MAP,n.TEXTURE_CUBE_MAP_POSITIVE_X,6),Y[n.TEXTURE_2D_ARRAY]=it(n.TEXTURE_2D_ARRAY,n.TEXTURE_2D_ARRAY,1,1),Y[n.TEXTURE_3D]=it(n.TEXTURE_3D,n.TEXTURE_3D,1,1),r.setClear(0,0,0,1),a.setClear(1),o.setClear(0),se(n.DEPTH_TEST),a.setFunc(Ci),Z(!1),$(kl),se(n.CULL_FACE),ne(Xn);function se(I){u[I]!==!0&&(n.enable(I),u[I]=!0)}function Me(I){u[I]!==!1&&(n.disable(I),u[I]=!1)}function Ue(I,ce){return h[I]!==ce?(n.bindFramebuffer(I,ce),h[I]=ce,I===n.DRAW_FRAMEBUFFER&&(h[n.FRAMEBUFFER]=ce),I===n.FRAMEBUFFER&&(h[n.DRAW_FRAMEBUFFER]=ce),!0):!1}function Ae(I,ce){let ge=f,Se=!1;if(I){ge=d.get(ce),ge===void 0&&(ge=[],d.set(ce,ge));let oe=I.textures;if(ge.length!==oe.length||ge[0]!==n.COLOR_ATTACHMENT0){for(let K=0,Pe=oe.length;K<Pe;K++)ge[K]=n.COLOR_ATTACHMENT0+K;ge.length=oe.length,Se=!0}}else ge[0]!==n.BACK&&(ge[0]=n.BACK,Se=!0);Se&&n.drawBuffers(ge)}function et(I){return g!==I?(n.useProgram(I),g=I,!0):!1}let ft={[ri]:n.FUNC_ADD,[Jh]:n.FUNC_SUBTRACT,[Kh]:n.FUNC_REVERSE_SUBTRACT};ft[jh]=n.MIN,ft[Qh]=n.MAX;let A={[eu]:n.ZERO,[tu]:n.ONE,[nu]:n.SRC_COLOR,[ua]:n.SRC_ALPHA,[lu]:n.SRC_ALPHA_SATURATE,[au]:n.DST_COLOR,[su]:n.DST_ALPHA,[iu]:n.ONE_MINUS_SRC_COLOR,[da]:n.ONE_MINUS_SRC_ALPHA,[ou]:n.ONE_MINUS_DST_COLOR,[ru]:n.ONE_MINUS_DST_ALPHA,[cu]:n.CONSTANT_COLOR,[hu]:n.ONE_MINUS_CONSTANT_COLOR,[uu]:n.CONSTANT_ALPHA,[du]:n.ONE_MINUS_CONSTANT_ALPHA};function ne(I,ce,ge,Se,oe,K,Pe,Xe,pt,at){if(I===Xn){x===!0&&(Me(n.BLEND),x=!1);return}if(x===!1&&(se(n.BLEND),x=!0),I!==Zh){if(I!==m||at!==b){if((p!==ri||y!==ri)&&(n.blendEquation(n.FUNC_ADD),p=ri,y=ri),at)switch(I){case Ai:n.blendFuncSeparate(n.ONE,n.ONE_MINUS_SRC_ALPHA,n.ONE,n.ONE_MINUS_SRC_ALPHA);break;case zl:n.blendFunc(n.ONE,n.ONE);break;case Vl:n.blendFuncSeparate(n.ZERO,n.ONE_MINUS_SRC_COLOR,n.ZERO,n.ONE);break;case Hl:n.blendFuncSeparate(n.DST_COLOR,n.ONE_MINUS_SRC_ALPHA,n.ZERO,n.ONE);break;default:console.error("THREE.WebGLState: Invalid blending: ",I);break}else switch(I){case Ai:n.blendFuncSeparate(n.SRC_ALPHA,n.ONE_MINUS_SRC_ALPHA,n.ONE,n.ONE_MINUS_SRC_ALPHA);break;case zl:n.blendFuncSeparate(n.SRC_ALPHA,n.ONE,n.ONE,n.ONE);break;case Vl:console.error("THREE.WebGLState: SubtractiveBlending requires material.premultipliedAlpha = true");break;case Hl:console.error("THREE.WebGLState: MultiplyBlending requires material.premultipliedAlpha = true");break;default:console.error("THREE.WebGLState: Invalid blending: ",I);break}T=null,M=null,R=null,E=null,P.set(0,0,0),D=0,m=I,b=at}return}oe=oe||ce,K=K||ge,Pe=Pe||Se,(ce!==p||oe!==y)&&(n.blendEquationSeparate(ft[ce],ft[oe]),p=ce,y=oe),(ge!==T||Se!==M||K!==R||Pe!==E)&&(n.blendFuncSeparate(A[ge],A[Se],A[K],A[Pe]),T=ge,M=Se,R=K,E=Pe),(Xe.equals(P)===!1||pt!==D)&&(n.blendColor(Xe.r,Xe.g,Xe.b,pt),P.copy(Xe),D=pt),m=I,b=!1}function J(I,ce){I.side===An?Me(n.CULL_FACE):se(n.CULL_FACE);let ge=I.side===Wt;ce&&(ge=!ge),Z(ge),I.blending===Ai&&I.transparent===!1?ne(Xn):ne(I.blending,I.blendEquation,I.blendSrc,I.blendDst,I.blendEquationAlpha,I.blendSrcAlpha,I.blendDstAlpha,I.blendColor,I.blendAlpha,I.premultipliedAlpha),a.setFunc(I.depthFunc),a.setTest(I.depthTest),a.setMask(I.depthWrite),r.setMask(I.colorWrite);let Se=I.stencilWrite;o.setTest(Se),Se&&(o.setMask(I.stencilWriteMask),o.setFunc(I.stencilFunc,I.stencilRef,I.stencilFuncMask),o.setOp(I.stencilFail,I.stencilZFail,I.stencilZPass)),re(I.polygonOffset,I.polygonOffsetFactor,I.polygonOffsetUnits),I.alphaToCoverage===!0?se(n.SAMPLE_ALPHA_TO_COVERAGE):Me(n.SAMPLE_ALPHA_TO_COVERAGE)}function Z(I){w!==I&&(I?n.frontFace(n.CW):n.frontFace(n.CCW),w=I)}function $(I){I!==Yh?(se(n.CULL_FACE),I!==C&&(I===kl?n.cullFace(n.BACK):I===$h?n.cullFace(n.FRONT):n.cullFace(n.FRONT_AND_BACK))):Me(n.CULL_FACE),C=I}function pe(I){I!==k&&(V&&n.lineWidth(I),k=I)}function re(I,ce,ge){I?(se(n.POLYGON_OFFSET_FILL),(G!==ce||q!==ge)&&(n.polygonOffset(ce,ge),G=ce,q=ge)):Me(n.POLYGON_OFFSET_FILL)}function me(I){I?se(n.SCISSOR_TEST):Me(n.SCISSOR_TEST)}function We(I){I===void 0&&(I=n.TEXTURE0+X-1),Q!==I&&(n.activeTexture(I),Q=I)}function He(I,ce,ge){ge===void 0&&(Q===null?ge=n.TEXTURE0+X-1:ge=Q);let Se=he[ge];Se===void 0&&(Se={type:void 0,texture:void 0},he[ge]=Se),(Se.type!==I||Se.texture!==ce)&&(Q!==ge&&(n.activeTexture(ge),Q=ge),n.bindTexture(I,ce||Y[I]),Se.type=I,Se.texture=ce)}function S(){let I=he[Q];I!==void 0&&I.type!==void 0&&(n.bindTexture(I.type,null),I.type=void 0,I.texture=void 0)}function _(){try{n.compressedTexImage2D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function O(){try{n.compressedTexImage3D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function H(){try{n.texSubImage2D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function ee(){try{n.texSubImage3D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function W(){try{n.compressedTexSubImage2D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function Ne(){try{n.compressedTexSubImage3D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function fe(){try{n.texStorage2D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function Ce(){try{n.texStorage3D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function Re(){try{n.texImage2D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function ae(){try{n.texImage3D(...arguments)}catch(I){console.error("THREE.WebGLState:",I)}}function we(I){je.equals(I)===!1&&(n.scissor(I.x,I.y,I.z,I.w),je.copy(I))}function Be(I){Qe.equals(I)===!1&&(n.viewport(I.x,I.y,I.z,I.w),Qe.copy(I))}function Le(I,ce){let ge=l.get(ce);ge===void 0&&(ge=new WeakMap,l.set(ce,ge));let Se=ge.get(I);Se===void 0&&(Se=n.getUniformBlockIndex(ce,I.name),ge.set(I,Se))}function ve(I,ce){let Se=l.get(ce).get(I);c.get(ce)!==Se&&(n.uniformBlockBinding(ce,Se,I.__bindingPointIndex),c.set(ce,Se))}function Ze(){n.disable(n.BLEND),n.disable(n.CULL_FACE),n.disable(n.DEPTH_TEST),n.disable(n.POLYGON_OFFSET_FILL),n.disable(n.SCISSOR_TEST),n.disable(n.STENCIL_TEST),n.disable(n.SAMPLE_ALPHA_TO_COVERAGE),n.blendEquation(n.FUNC_ADD),n.blendFunc(n.ONE,n.ZERO),n.blendFuncSeparate(n.ONE,n.ZERO,n.ONE,n.ZERO),n.blendColor(0,0,0,0),n.colorMask(!0,!0,!0,!0),n.clearColor(0,0,0,0),n.depthMask(!0),n.depthFunc(n.LESS),a.setReversed(!1),n.clearDepth(1),n.stencilMask(4294967295),n.stencilFunc(n.ALWAYS,0,4294967295),n.stencilOp(n.KEEP,n.KEEP,n.KEEP),n.clearStencil(0),n.cullFace(n.BACK),n.frontFace(n.CCW),n.polygonOffset(0,0),n.activeTexture(n.TEXTURE0),n.bindFramebuffer(n.FRAMEBUFFER,null),n.bindFramebuffer(n.DRAW_FRAMEBUFFER,null),n.bindFramebuffer(n.READ_FRAMEBUFFER,null),n.useProgram(null),n.lineWidth(1),n.scissor(0,0,n.canvas.width,n.canvas.height),n.viewport(0,0,n.canvas.width,n.canvas.height),u={},Q=null,he={},h={},d=new WeakMap,f=[],g=null,x=!1,m=null,p=null,T=null,M=null,y=null,R=null,E=null,P=new qe(0,0,0),D=0,b=!1,w=null,C=null,k=null,G=null,q=null,je.set(0,0,n.canvas.width,n.canvas.height),Qe.set(0,0,n.canvas.width,n.canvas.height),r.reset(),a.reset(),o.reset()}return{buffers:{color:r,depth:a,stencil:o},enable:se,disable:Me,bindFramebuffer:Ue,drawBuffers:Ae,useProgram:et,setBlending:ne,setMaterial:J,setFlipSided:Z,setCullFace:$,setLineWidth:pe,setPolygonOffset:re,setScissorTest:me,activeTexture:We,bindTexture:He,unbindTexture:S,compressedTexImage2D:_,compressedTexImage3D:O,texImage2D:Re,texImage3D:ae,updateUBOMapping:Le,uniformBlockBinding:ve,texStorage2D:fe,texStorage3D:Ce,texSubImage2D:H,texSubImage3D:ee,compressedTexSubImage2D:W,compressedTexSubImage3D:Ne,scissor:we,viewport:Be,reset:Ze}}function f0(n,e,t,i,s,r,a){let o=e.has("WEBGL_multisampled_render_to_texture")?e.get("WEBGL_multisampled_render_to_texture"):null,c=typeof navigator>"u"?!1:/OculusBrowser/g.test(navigator.userAgent),l=new de,u=new WeakMap,h,d=new WeakMap,f=!1;try{f=typeof OffscreenCanvas<"u"&&new OffscreenCanvas(1,1).getContext("2d")!==null}catch{}function g(S,_){return f?new OffscreenCanvas(S,_):Zs("canvas")}function x(S,_,O){let H=1,ee=He(S);if((ee.width>O||ee.height>O)&&(H=O/Math.max(ee.width,ee.height)),H<1)if(typeof HTMLImageElement<"u"&&S instanceof HTMLImageElement||typeof HTMLCanvasElement<"u"&&S instanceof HTMLCanvasElement||typeof ImageBitmap<"u"&&S instanceof ImageBitmap||typeof VideoFrame<"u"&&S instanceof VideoFrame){let W=Math.floor(H*ee.width),Ne=Math.floor(H*ee.height);h===void 0&&(h=g(W,Ne));let fe=_?g(W,Ne):h;return fe.width=W,fe.height=Ne,fe.getContext("2d").drawImage(S,0,0,W,Ne),console.warn("THREE.WebGLRenderer: Texture has been resized from ("+ee.width+"x"+ee.height+") to ("+W+"x"+Ne+")."),fe}else return"data"in S&&console.warn("THREE.WebGLRenderer: Image in DataTexture is too big ("+ee.width+"x"+ee.height+")."),S;return S}function m(S){return S.generateMipmaps}function p(S){n.generateMipmap(S)}function T(S){return S.isWebGLCubeRenderTarget?n.TEXTURE_CUBE_MAP:S.isWebGL3DRenderTarget?n.TEXTURE_3D:S.isWebGLArrayRenderTarget||S.isCompressedArrayTexture?n.TEXTURE_2D_ARRAY:n.TEXTURE_2D}function M(S,_,O,H,ee=!1){if(S!==null){if(n[S]!==void 0)return n[S];console.warn("THREE.WebGLRenderer: Attempt to use non-existing WebGL internal format '"+S+"'")}let W=_;if(_===n.RED&&(O===n.FLOAT&&(W=n.R32F),O===n.HALF_FLOAT&&(W=n.R16F),O===n.UNSIGNED_BYTE&&(W=n.R8)),_===n.RED_INTEGER&&(O===n.UNSIGNED_BYTE&&(W=n.R8UI),O===n.UNSIGNED_SHORT&&(W=n.R16UI),O===n.UNSIGNED_INT&&(W=n.R32UI),O===n.BYTE&&(W=n.R8I),O===n.SHORT&&(W=n.R16I),O===n.INT&&(W=n.R32I)),_===n.RG&&(O===n.FLOAT&&(W=n.RG32F),O===n.HALF_FLOAT&&(W=n.RG16F),O===n.UNSIGNED_BYTE&&(W=n.RG8)),_===n.RG_INTEGER&&(O===n.UNSIGNED_BYTE&&(W=n.RG8UI),O===n.UNSIGNED_SHORT&&(W=n.RG16UI),O===n.UNSIGNED_INT&&(W=n.RG32UI),O===n.BYTE&&(W=n.RG8I),O===n.SHORT&&(W=n.RG16I),O===n.INT&&(W=n.RG32I)),_===n.RGB_INTEGER&&(O===n.UNSIGNED_BYTE&&(W=n.RGB8UI),O===n.UNSIGNED_SHORT&&(W=n.RGB16UI),O===n.UNSIGNED_INT&&(W=n.RGB32UI),O===n.BYTE&&(W=n.RGB8I),O===n.SHORT&&(W=n.RGB16I),O===n.INT&&(W=n.RGB32I)),_===n.RGBA_INTEGER&&(O===n.UNSIGNED_BYTE&&(W=n.RGBA8UI),O===n.UNSIGNED_SHORT&&(W=n.RGBA16UI),O===n.UNSIGNED_INT&&(W=n.RGBA32UI),O===n.BYTE&&(W=n.RGBA8I),O===n.SHORT&&(W=n.RGBA16I),O===n.INT&&(W=n.RGBA32I)),_===n.RGB&&(O===n.UNSIGNED_INT_5_9_9_9_REV&&(W=n.RGB9_E5),O===n.UNSIGNED_INT_10F_11F_11F_REV&&(W=n.R11F_G11F_B10F)),_===n.RGBA){let Ne=ee?Ys:st.getTransfer(H);O===n.FLOAT&&(W=n.RGBA32F),O===n.HALF_FLOAT&&(W=n.RGBA16F),O===n.UNSIGNED_BYTE&&(W=Ne===ot?n.SRGB8_ALPHA8:n.RGBA8),O===n.UNSIGNED_SHORT_4_4_4_4&&(W=n.RGBA4),O===n.UNSIGNED_SHORT_5_5_5_1&&(W=n.RGB5_A1)}return(W===n.R16F||W===n.R32F||W===n.RG16F||W===n.RG32F||W===n.RGBA16F||W===n.RGBA32F)&&e.get("EXT_color_buffer_float"),W}function y(S,_){let O;return S?_===null||_===mi||_===ws?O=n.DEPTH24_STENCIL8:_===Cn?O=n.DEPTH32F_STENCIL8:_===vs&&(O=n.DEPTH24_STENCIL8,console.warn("DepthTexture: 16 bit depth attachment is not supported with stencil. Using 24-bit attachment.")):_===null||_===mi||_===ws?O=n.DEPTH_COMPONENT24:_===Cn?O=n.DEPTH_COMPONENT32F:_===vs&&(O=n.DEPTH_COMPONENT16),O}function R(S,_){return m(S)===!0||S.isFramebufferTexture&&S.minFilter!==on&&S.minFilter!==gn?Math.log2(Math.max(_.width,_.height))+1:S.mipmaps!==void 0&&S.mipmaps.length>0?S.mipmaps.length:S.isCompressedTexture&&Array.isArray(S.image)?_.mipmaps.length:1}function E(S){let _=S.target;_.removeEventListener("dispose",E),D(_),_.isVideoTexture&&u.delete(_)}function P(S){let _=S.target;_.removeEventListener("dispose",P),w(_)}function D(S){let _=i.get(S);if(_.__webglInit===void 0)return;let O=S.source,H=d.get(O);if(H){let ee=H[_.__cacheKey];ee.usedTimes--,ee.usedTimes===0&&b(S),Object.keys(H).length===0&&d.delete(O)}i.remove(S)}function b(S){let _=i.get(S);n.deleteTexture(_.__webglTexture);let O=S.source,H=d.get(O);delete H[_.__cacheKey],a.memory.textures--}function w(S){let _=i.get(S);if(S.depthTexture&&(S.depthTexture.dispose(),i.remove(S.depthTexture)),S.isWebGLCubeRenderTarget)for(let H=0;H<6;H++){if(Array.isArray(_.__webglFramebuffer[H]))for(let ee=0;ee<_.__webglFramebuffer[H].length;ee++)n.deleteFramebuffer(_.__webglFramebuffer[H][ee]);else n.deleteFramebuffer(_.__webglFramebuffer[H]);_.__webglDepthbuffer&&n.deleteRenderbuffer(_.__webglDepthbuffer[H])}else{if(Array.isArray(_.__webglFramebuffer))for(let H=0;H<_.__webglFramebuffer.length;H++)n.deleteFramebuffer(_.__webglFramebuffer[H]);else n.deleteFramebuffer(_.__webglFramebuffer);if(_.__webglDepthbuffer&&n.deleteRenderbuffer(_.__webglDepthbuffer),_.__webglMultisampledFramebuffer&&n.deleteFramebuffer(_.__webglMultisampledFramebuffer),_.__webglColorRenderbuffer)for(let H=0;H<_.__webglColorRenderbuffer.length;H++)_.__webglColorRenderbuffer[H]&&n.deleteRenderbuffer(_.__webglColorRenderbuffer[H]);_.__webglDepthRenderbuffer&&n.deleteRenderbuffer(_.__webglDepthRenderbuffer)}let O=S.textures;for(let H=0,ee=O.length;H<ee;H++){let W=i.get(O[H]);W.__webglTexture&&(n.deleteTexture(W.__webglTexture),a.memory.textures--),i.remove(O[H])}i.remove(S)}let C=0;function k(){C=0}function G(){let S=C;return S>=s.maxTextures&&console.warn("THREE.WebGLTextures: Trying to use "+S+" texture units while this GPU supports only "+s.maxTextures),C+=1,S}function q(S){let _=[];return _.push(S.wrapS),_.push(S.wrapT),_.push(S.wrapR||0),_.push(S.magFilter),_.push(S.minFilter),_.push(S.anisotropy),_.push(S.internalFormat),_.push(S.format),_.push(S.type),_.push(S.generateMipmaps),_.push(S.premultiplyAlpha),_.push(S.flipY),_.push(S.unpackAlignment),_.push(S.colorSpace),_.join()}function X(S,_){let O=i.get(S);if(S.isVideoTexture&&me(S),S.isRenderTargetTexture===!1&&S.isExternalTexture!==!0&&S.version>0&&O.__version!==S.version){let H=S.image;if(H===null)console.warn("THREE.WebGLRenderer: Texture marked for update but no image data found.");else if(H.complete===!1)console.warn("THREE.WebGLRenderer: Texture marked for update but image is incomplete");else{Y(O,S,_);return}}else S.isExternalTexture&&(O.__webglTexture=S.sourceTexture?S.sourceTexture:null);t.bindTexture(n.TEXTURE_2D,O.__webglTexture,n.TEXTURE0+_)}function V(S,_){let O=i.get(S);if(S.isRenderTargetTexture===!1&&S.version>0&&O.__version!==S.version){Y(O,S,_);return}t.bindTexture(n.TEXTURE_2D_ARRAY,O.__webglTexture,n.TEXTURE0+_)}function te(S,_){let O=i.get(S);if(S.isRenderTargetTexture===!1&&S.version>0&&O.__version!==S.version){Y(O,S,_);return}t.bindTexture(n.TEXTURE_3D,O.__webglTexture,n.TEXTURE0+_)}function U(S,_){let O=i.get(S);if(S.version>0&&O.__version!==S.version){se(O,S,_);return}t.bindTexture(n.TEXTURE_CUBE_MAP,O.__webglTexture,n.TEXTURE0+_)}let Q={[fa]:n.REPEAT,[si]:n.CLAMP_TO_EDGE,[pa]:n.MIRRORED_REPEAT},he={[on]:n.NEAREST,[bu]:n.NEAREST_MIPMAP_NEAREST,[Sr]:n.NEAREST_MIPMAP_LINEAR,[gn]:n.LINEAR,[$a]:n.LINEAR_MIPMAP_NEAREST,[pi]:n.LINEAR_MIPMAP_LINEAR},ue={[Eu]:n.NEVER,[Nu]:n.ALWAYS,[Au]:n.LESS,[ec]:n.LEQUAL,[Cu]:n.EQUAL,[Iu]:n.GEQUAL,[Ru]:n.GREATER,[Pu]:n.NOTEQUAL};function ze(S,_){if(_.type===Cn&&e.has("OES_texture_float_linear")===!1&&(_.magFilter===gn||_.magFilter===$a||_.magFilter===Sr||_.magFilter===pi||_.minFilter===gn||_.minFilter===$a||_.minFilter===Sr||_.minFilter===pi)&&console.warn("THREE.WebGLRenderer: Unable to use linear filtering with floating point textures. OES_texture_float_linear not supported on this device."),n.texParameteri(S,n.TEXTURE_WRAP_S,Q[_.wrapS]),n.texParameteri(S,n.TEXTURE_WRAP_T,Q[_.wrapT]),(S===n.TEXTURE_3D||S===n.TEXTURE_2D_ARRAY)&&n.texParameteri(S,n.TEXTURE_WRAP_R,Q[_.wrapR]),n.texParameteri(S,n.TEXTURE_MAG_FILTER,he[_.magFilter]),n.texParameteri(S,n.TEXTURE_MIN_FILTER,he[_.minFilter]),_.compareFunction&&(n.texParameteri(S,n.TEXTURE_COMPARE_MODE,n.COMPARE_REF_TO_TEXTURE),n.texParameteri(S,n.TEXTURE_COMPARE_FUNC,ue[_.compareFunction])),e.has("EXT_texture_filter_anisotropic")===!0){if(_.magFilter===on||_.minFilter!==Sr&&_.minFilter!==pi||_.type===Cn&&e.has("OES_texture_float_linear")===!1)return;if(_.anisotropy>1||i.get(_).__currentAnisotropy){let O=e.get("EXT_texture_filter_anisotropic");n.texParameterf(S,O.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(_.anisotropy,s.getMaxAnisotropy())),i.get(_).__currentAnisotropy=_.anisotropy}}}function je(S,_){let O=!1;S.__webglInit===void 0&&(S.__webglInit=!0,_.addEventListener("dispose",E));let H=_.source,ee=d.get(H);ee===void 0&&(ee={},d.set(H,ee));let W=q(_);if(W!==S.__cacheKey){ee[W]===void 0&&(ee[W]={texture:n.createTexture(),usedTimes:0},a.memory.textures++,O=!0),ee[W].usedTimes++;let Ne=ee[S.__cacheKey];Ne!==void 0&&(ee[S.__cacheKey].usedTimes--,Ne.usedTimes===0&&b(_)),S.__cacheKey=W,S.__webglTexture=ee[W].texture}return O}function Qe(S,_,O){return Math.floor(Math.floor(S/O)/_)}function it(S,_,O,H){let W=S.updateRanges;if(W.length===0)t.texSubImage2D(n.TEXTURE_2D,0,0,0,_.width,_.height,O,H,_.data);else{W.sort((ae,we)=>ae.start-we.start);let Ne=0;for(let ae=1;ae<W.length;ae++){let we=W[Ne],Be=W[ae],Le=we.start+we.count,ve=Qe(Be.start,_.width,4),Ze=Qe(we.start,_.width,4);Be.start<=Le+1&&ve===Ze&&Qe(Be.start+Be.count-1,_.width,4)===ve?we.count=Math.max(we.count,Be.start+Be.count-we.start):(++Ne,W[Ne]=Be)}W.length=Ne+1;let fe=n.getParameter(n.UNPACK_ROW_LENGTH),Ce=n.getParameter(n.UNPACK_SKIP_PIXELS),Re=n.getParameter(n.UNPACK_SKIP_ROWS);n.pixelStorei(n.UNPACK_ROW_LENGTH,_.width);for(let ae=0,we=W.length;ae<we;ae++){let Be=W[ae],Le=Math.floor(Be.start/4),ve=Math.ceil(Be.count/4),Ze=Le%_.width,I=Math.floor(Le/_.width),ce=ve,ge=1;n.pixelStorei(n.UNPACK_SKIP_PIXELS,Ze),n.pixelStorei(n.UNPACK_SKIP_ROWS,I),t.texSubImage2D(n.TEXTURE_2D,0,Ze,I,ce,ge,O,H,_.data)}S.clearUpdateRanges(),n.pixelStorei(n.UNPACK_ROW_LENGTH,fe),n.pixelStorei(n.UNPACK_SKIP_PIXELS,Ce),n.pixelStorei(n.UNPACK_SKIP_ROWS,Re)}}function Y(S,_,O){let H=n.TEXTURE_2D;(_.isDataArrayTexture||_.isCompressedArrayTexture)&&(H=n.TEXTURE_2D_ARRAY),_.isData3DTexture&&(H=n.TEXTURE_3D);let ee=je(S,_),W=_.source;t.bindTexture(H,S.__webglTexture,n.TEXTURE0+O);let Ne=i.get(W);if(W.version!==Ne.__version||ee===!0){t.activeTexture(n.TEXTURE0+O);let fe=st.getPrimaries(st.workingColorSpace),Ce=_.colorSpace===Yn?null:st.getPrimaries(_.colorSpace),Re=_.colorSpace===Yn||fe===Ce?n.NONE:n.BROWSER_DEFAULT_WEBGL;n.pixelStorei(n.UNPACK_FLIP_Y_WEBGL,_.flipY),n.pixelStorei(n.UNPACK_PREMULTIPLY_ALPHA_WEBGL,_.premultiplyAlpha),n.pixelStorei(n.UNPACK_ALIGNMENT,_.unpackAlignment),n.pixelStorei(n.UNPACK_COLORSPACE_CONVERSION_WEBGL,Re);let ae=x(_.image,!1,s.maxTextureSize);ae=We(_,ae);let we=r.convert(_.format,_.colorSpace),Be=r.convert(_.type),Le=M(_.internalFormat,we,Be,_.colorSpace,_.isVideoTexture);ze(H,_);let ve,Ze=_.mipmaps,I=_.isVideoTexture!==!0,ce=Ne.__version===void 0||ee===!0,ge=W.dataReady,Se=R(_,ae);if(_.isDepthTexture)Le=y(_.format===bs,_.type),ce&&(I?t.texStorage2D(n.TEXTURE_2D,1,Le,ae.width,ae.height):t.texImage2D(n.TEXTURE_2D,0,Le,ae.width,ae.height,0,we,Be,null));else if(_.isDataTexture)if(Ze.length>0){I&&ce&&t.texStorage2D(n.TEXTURE_2D,Se,Le,Ze[0].width,Ze[0].height);for(let oe=0,K=Ze.length;oe<K;oe++)ve=Ze[oe],I?ge&&t.texSubImage2D(n.TEXTURE_2D,oe,0,0,ve.width,ve.height,we,Be,ve.data):t.texImage2D(n.TEXTURE_2D,oe,Le,ve.width,ve.height,0,we,Be,ve.data);_.generateMipmaps=!1}else I?(ce&&t.texStorage2D(n.TEXTURE_2D,Se,Le,ae.width,ae.height),ge&&it(_,ae,we,Be)):t.texImage2D(n.TEXTURE_2D,0,Le,ae.width,ae.height,0,we,Be,ae.data);else if(_.isCompressedTexture)if(_.isCompressedArrayTexture){I&&ce&&t.texStorage3D(n.TEXTURE_2D_ARRAY,Se,Le,Ze[0].width,Ze[0].height,ae.depth);for(let oe=0,K=Ze.length;oe<K;oe++)if(ve=Ze[oe],_.format!==hn)if(we!==null)if(I){if(ge)if(_.layerUpdates.size>0){let Pe=cc(ve.width,ve.height,_.format,_.type);for(let Xe of _.layerUpdates){let pt=ve.data.subarray(Xe*Pe/ve.data.BYTES_PER_ELEMENT,(Xe+1)*Pe/ve.data.BYTES_PER_ELEMENT);t.compressedTexSubImage3D(n.TEXTURE_2D_ARRAY,oe,0,0,Xe,ve.width,ve.height,1,we,pt)}_.clearLayerUpdates()}else t.compressedTexSubImage3D(n.TEXTURE_2D_ARRAY,oe,0,0,0,ve.width,ve.height,ae.depth,we,ve.data)}else t.compressedTexImage3D(n.TEXTURE_2D_ARRAY,oe,Le,ve.width,ve.height,ae.depth,0,ve.data,0,0);else console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()");else I?ge&&t.texSubImage3D(n.TEXTURE_2D_ARRAY,oe,0,0,0,ve.width,ve.height,ae.depth,we,Be,ve.data):t.texImage3D(n.TEXTURE_2D_ARRAY,oe,Le,ve.width,ve.height,ae.depth,0,we,Be,ve.data)}else{I&&ce&&t.texStorage2D(n.TEXTURE_2D,Se,Le,Ze[0].width,Ze[0].height);for(let oe=0,K=Ze.length;oe<K;oe++)ve=Ze[oe],_.format!==hn?we!==null?I?ge&&t.compressedTexSubImage2D(n.TEXTURE_2D,oe,0,0,ve.width,ve.height,we,ve.data):t.compressedTexImage2D(n.TEXTURE_2D,oe,Le,ve.width,ve.height,0,ve.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .uploadTexture()"):I?ge&&t.texSubImage2D(n.TEXTURE_2D,oe,0,0,ve.width,ve.height,we,Be,ve.data):t.texImage2D(n.TEXTURE_2D,oe,Le,ve.width,ve.height,0,we,Be,ve.data)}else if(_.isDataArrayTexture)if(I){if(ce&&t.texStorage3D(n.TEXTURE_2D_ARRAY,Se,Le,ae.width,ae.height,ae.depth),ge)if(_.layerUpdates.size>0){let oe=cc(ae.width,ae.height,_.format,_.type);for(let K of _.layerUpdates){let Pe=ae.data.subarray(K*oe/ae.data.BYTES_PER_ELEMENT,(K+1)*oe/ae.data.BYTES_PER_ELEMENT);t.texSubImage3D(n.TEXTURE_2D_ARRAY,0,0,0,K,ae.width,ae.height,1,we,Be,Pe)}_.clearLayerUpdates()}else t.texSubImage3D(n.TEXTURE_2D_ARRAY,0,0,0,0,ae.width,ae.height,ae.depth,we,Be,ae.data)}else t.texImage3D(n.TEXTURE_2D_ARRAY,0,Le,ae.width,ae.height,ae.depth,0,we,Be,ae.data);else if(_.isData3DTexture)I?(ce&&t.texStorage3D(n.TEXTURE_3D,Se,Le,ae.width,ae.height,ae.depth),ge&&t.texSubImage3D(n.TEXTURE_3D,0,0,0,0,ae.width,ae.height,ae.depth,we,Be,ae.data)):t.texImage3D(n.TEXTURE_3D,0,Le,ae.width,ae.height,ae.depth,0,we,Be,ae.data);else if(_.isFramebufferTexture){if(ce)if(I)t.texStorage2D(n.TEXTURE_2D,Se,Le,ae.width,ae.height);else{let oe=ae.width,K=ae.height;for(let Pe=0;Pe<Se;Pe++)t.texImage2D(n.TEXTURE_2D,Pe,Le,oe,K,0,we,Be,null),oe>>=1,K>>=1}}else if(Ze.length>0){if(I&&ce){let oe=He(Ze[0]);t.texStorage2D(n.TEXTURE_2D,Se,Le,oe.width,oe.height)}for(let oe=0,K=Ze.length;oe<K;oe++)ve=Ze[oe],I?ge&&t.texSubImage2D(n.TEXTURE_2D,oe,0,0,we,Be,ve):t.texImage2D(n.TEXTURE_2D,oe,Le,we,Be,ve);_.generateMipmaps=!1}else if(I){if(ce){let oe=He(ae);t.texStorage2D(n.TEXTURE_2D,Se,Le,oe.width,oe.height)}ge&&t.texSubImage2D(n.TEXTURE_2D,0,0,0,we,Be,ae)}else t.texImage2D(n.TEXTURE_2D,0,Le,we,Be,ae);m(_)&&p(H),Ne.__version=W.version,_.onUpdate&&_.onUpdate(_)}S.__version=_.version}function se(S,_,O){if(_.image.length!==6)return;let H=je(S,_),ee=_.source;t.bindTexture(n.TEXTURE_CUBE_MAP,S.__webglTexture,n.TEXTURE0+O);let W=i.get(ee);if(ee.version!==W.__version||H===!0){t.activeTexture(n.TEXTURE0+O);let Ne=st.getPrimaries(st.workingColorSpace),fe=_.colorSpace===Yn?null:st.getPrimaries(_.colorSpace),Ce=_.colorSpace===Yn||Ne===fe?n.NONE:n.BROWSER_DEFAULT_WEBGL;n.pixelStorei(n.UNPACK_FLIP_Y_WEBGL,_.flipY),n.pixelStorei(n.UNPACK_PREMULTIPLY_ALPHA_WEBGL,_.premultiplyAlpha),n.pixelStorei(n.UNPACK_ALIGNMENT,_.unpackAlignment),n.pixelStorei(n.UNPACK_COLORSPACE_CONVERSION_WEBGL,Ce);let Re=_.isCompressedTexture||_.image[0].isCompressedTexture,ae=_.image[0]&&_.image[0].isDataTexture,we=[];for(let K=0;K<6;K++)!Re&&!ae?we[K]=x(_.image[K],!0,s.maxCubemapSize):we[K]=ae?_.image[K].image:_.image[K],we[K]=We(_,we[K]);let Be=we[0],Le=r.convert(_.format,_.colorSpace),ve=r.convert(_.type),Ze=M(_.internalFormat,Le,ve,_.colorSpace),I=_.isVideoTexture!==!0,ce=W.__version===void 0||H===!0,ge=ee.dataReady,Se=R(_,Be);ze(n.TEXTURE_CUBE_MAP,_);let oe;if(Re){I&&ce&&t.texStorage2D(n.TEXTURE_CUBE_MAP,Se,Ze,Be.width,Be.height);for(let K=0;K<6;K++){oe=we[K].mipmaps;for(let Pe=0;Pe<oe.length;Pe++){let Xe=oe[Pe];_.format!==hn?Le!==null?I?ge&&t.compressedTexSubImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe,0,0,Xe.width,Xe.height,Le,Xe.data):t.compressedTexImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe,Ze,Xe.width,Xe.height,0,Xe.data):console.warn("THREE.WebGLRenderer: Attempt to load unsupported compressed texture format in .setTextureCube()"):I?ge&&t.texSubImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe,0,0,Xe.width,Xe.height,Le,ve,Xe.data):t.texImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe,Ze,Xe.width,Xe.height,0,Le,ve,Xe.data)}}}else{if(oe=_.mipmaps,I&&ce){oe.length>0&&Se++;let K=He(we[0]);t.texStorage2D(n.TEXTURE_CUBE_MAP,Se,Ze,K.width,K.height)}for(let K=0;K<6;K++)if(ae){I?ge&&t.texSubImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,0,0,we[K].width,we[K].height,Le,ve,we[K].data):t.texImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,Ze,we[K].width,we[K].height,0,Le,ve,we[K].data);for(let Pe=0;Pe<oe.length;Pe++){let pt=oe[Pe].image[K].image;I?ge&&t.texSubImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe+1,0,0,pt.width,pt.height,Le,ve,pt.data):t.texImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe+1,Ze,pt.width,pt.height,0,Le,ve,pt.data)}}else{I?ge&&t.texSubImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,0,0,Le,ve,we[K]):t.texImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,0,Ze,Le,ve,we[K]);for(let Pe=0;Pe<oe.length;Pe++){let Xe=oe[Pe];I?ge&&t.texSubImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe+1,0,0,Le,ve,Xe.image[K]):t.texImage2D(n.TEXTURE_CUBE_MAP_POSITIVE_X+K,Pe+1,Ze,Le,ve,Xe.image[K])}}}m(_)&&p(n.TEXTURE_CUBE_MAP),W.__version=ee.version,_.onUpdate&&_.onUpdate(_)}S.__version=_.version}function Me(S,_,O,H,ee,W){let Ne=r.convert(O.format,O.colorSpace),fe=r.convert(O.type),Ce=M(O.internalFormat,Ne,fe,O.colorSpace),Re=i.get(_),ae=i.get(O);if(ae.__renderTarget=_,!Re.__hasExternalTextures){let we=Math.max(1,_.width>>W),Be=Math.max(1,_.height>>W);ee===n.TEXTURE_3D||ee===n.TEXTURE_2D_ARRAY?t.texImage3D(ee,W,Ce,we,Be,_.depth,0,Ne,fe,null):t.texImage2D(ee,W,Ce,we,Be,0,Ne,fe,null)}t.bindFramebuffer(n.FRAMEBUFFER,S),re(_)?o.framebufferTexture2DMultisampleEXT(n.FRAMEBUFFER,H,ee,ae.__webglTexture,0,pe(_)):(ee===n.TEXTURE_2D||ee>=n.TEXTURE_CUBE_MAP_POSITIVE_X&&ee<=n.TEXTURE_CUBE_MAP_NEGATIVE_Z)&&n.framebufferTexture2D(n.FRAMEBUFFER,H,ee,ae.__webglTexture,W),t.bindFramebuffer(n.FRAMEBUFFER,null)}function Ue(S,_,O){if(n.bindRenderbuffer(n.RENDERBUFFER,S),_.depthBuffer){let H=_.depthTexture,ee=H&&H.isDepthTexture?H.type:null,W=y(_.stencilBuffer,ee),Ne=_.stencilBuffer?n.DEPTH_STENCIL_ATTACHMENT:n.DEPTH_ATTACHMENT,fe=pe(_);re(_)?o.renderbufferStorageMultisampleEXT(n.RENDERBUFFER,fe,W,_.width,_.height):O?n.renderbufferStorageMultisample(n.RENDERBUFFER,fe,W,_.width,_.height):n.renderbufferStorage(n.RENDERBUFFER,W,_.width,_.height),n.framebufferRenderbuffer(n.FRAMEBUFFER,Ne,n.RENDERBUFFER,S)}else{let H=_.textures;for(let ee=0;ee<H.length;ee++){let W=H[ee],Ne=r.convert(W.format,W.colorSpace),fe=r.convert(W.type),Ce=M(W.internalFormat,Ne,fe,W.colorSpace),Re=pe(_);O&&re(_)===!1?n.renderbufferStorageMultisample(n.RENDERBUFFER,Re,Ce,_.width,_.height):re(_)?o.renderbufferStorageMultisampleEXT(n.RENDERBUFFER,Re,Ce,_.width,_.height):n.renderbufferStorage(n.RENDERBUFFER,Ce,_.width,_.height)}}n.bindRenderbuffer(n.RENDERBUFFER,null)}function Ae(S,_){if(_&&_.isWebGLCubeRenderTarget)throw new Error("Depth Texture with cube render targets is not supported");if(t.bindFramebuffer(n.FRAMEBUFFER,S),!(_.depthTexture&&_.depthTexture.isDepthTexture))throw new Error("renderTarget.depthTexture must be an instance of THREE.DepthTexture");let H=i.get(_.depthTexture);H.__renderTarget=_,(!H.__webglTexture||_.depthTexture.image.width!==_.width||_.depthTexture.image.height!==_.height)&&(_.depthTexture.image.width=_.width,_.depthTexture.image.height=_.height,_.depthTexture.needsUpdate=!0),X(_.depthTexture,0);let ee=H.__webglTexture,W=pe(_);if(_.depthTexture.format===ls)re(_)?o.framebufferTexture2DMultisampleEXT(n.FRAMEBUFFER,n.DEPTH_ATTACHMENT,n.TEXTURE_2D,ee,0,W):n.framebufferTexture2D(n.FRAMEBUFFER,n.DEPTH_ATTACHMENT,n.TEXTURE_2D,ee,0);else if(_.depthTexture.format===bs)re(_)?o.framebufferTexture2DMultisampleEXT(n.FRAMEBUFFER,n.DEPTH_STENCIL_ATTACHMENT,n.TEXTURE_2D,ee,0,W):n.framebufferTexture2D(n.FRAMEBUFFER,n.DEPTH_STENCIL_ATTACHMENT,n.TEXTURE_2D,ee,0);else throw new Error("Unknown depthTexture format")}function et(S){let _=i.get(S),O=S.isWebGLCubeRenderTarget===!0;if(_.__boundDepthTexture!==S.depthTexture){let H=S.depthTexture;if(_.__depthDisposeCallback&&_.__depthDisposeCallback(),H){let ee=()=>{delete _.__boundDepthTexture,delete _.__depthDisposeCallback,H.removeEventListener("dispose",ee)};H.addEventListener("dispose",ee),_.__depthDisposeCallback=ee}_.__boundDepthTexture=H}if(S.depthTexture&&!_.__autoAllocateDepthBuffer){if(O)throw new Error("target.depthTexture not supported in Cube render targets");let H=S.texture.mipmaps;H&&H.length>0?Ae(_.__webglFramebuffer[0],S):Ae(_.__webglFramebuffer,S)}else if(O){_.__webglDepthbuffer=[];for(let H=0;H<6;H++)if(t.bindFramebuffer(n.FRAMEBUFFER,_.__webglFramebuffer[H]),_.__webglDepthbuffer[H]===void 0)_.__webglDepthbuffer[H]=n.createRenderbuffer(),Ue(_.__webglDepthbuffer[H],S,!1);else{let ee=S.stencilBuffer?n.DEPTH_STENCIL_ATTACHMENT:n.DEPTH_ATTACHMENT,W=_.__webglDepthbuffer[H];n.bindRenderbuffer(n.RENDERBUFFER,W),n.framebufferRenderbuffer(n.FRAMEBUFFER,ee,n.RENDERBUFFER,W)}}else{let H=S.texture.mipmaps;if(H&&H.length>0?t.bindFramebuffer(n.FRAMEBUFFER,_.__webglFramebuffer[0]):t.bindFramebuffer(n.FRAMEBUFFER,_.__webglFramebuffer),_.__webglDepthbuffer===void 0)_.__webglDepthbuffer=n.createRenderbuffer(),Ue(_.__webglDepthbuffer,S,!1);else{let ee=S.stencilBuffer?n.DEPTH_STENCIL_ATTACHMENT:n.DEPTH_ATTACHMENT,W=_.__webglDepthbuffer;n.bindRenderbuffer(n.RENDERBUFFER,W),n.framebufferRenderbuffer(n.FRAMEBUFFER,ee,n.RENDERBUFFER,W)}}t.bindFramebuffer(n.FRAMEBUFFER,null)}function ft(S,_,O){let H=i.get(S);_!==void 0&&Me(H.__webglFramebuffer,S,S.texture,n.COLOR_ATTACHMENT0,n.TEXTURE_2D,0),O!==void 0&&et(S)}function A(S){let _=S.texture,O=i.get(S),H=i.get(_);S.addEventListener("dispose",P);let ee=S.textures,W=S.isWebGLCubeRenderTarget===!0,Ne=ee.length>1;if(Ne||(H.__webglTexture===void 0&&(H.__webglTexture=n.createTexture()),H.__version=_.version,a.memory.textures++),W){O.__webglFramebuffer=[];for(let fe=0;fe<6;fe++)if(_.mipmaps&&_.mipmaps.length>0){O.__webglFramebuffer[fe]=[];for(let Ce=0;Ce<_.mipmaps.length;Ce++)O.__webglFramebuffer[fe][Ce]=n.createFramebuffer()}else O.__webglFramebuffer[fe]=n.createFramebuffer()}else{if(_.mipmaps&&_.mipmaps.length>0){O.__webglFramebuffer=[];for(let fe=0;fe<_.mipmaps.length;fe++)O.__webglFramebuffer[fe]=n.createFramebuffer()}else O.__webglFramebuffer=n.createFramebuffer();if(Ne)for(let fe=0,Ce=ee.length;fe<Ce;fe++){let Re=i.get(ee[fe]);Re.__webglTexture===void 0&&(Re.__webglTexture=n.createTexture(),a.memory.textures++)}if(S.samples>0&&re(S)===!1){O.__webglMultisampledFramebuffer=n.createFramebuffer(),O.__webglColorRenderbuffer=[],t.bindFramebuffer(n.FRAMEBUFFER,O.__webglMultisampledFramebuffer);for(let fe=0;fe<ee.length;fe++){let Ce=ee[fe];O.__webglColorRenderbuffer[fe]=n.createRenderbuffer(),n.bindRenderbuffer(n.RENDERBUFFER,O.__webglColorRenderbuffer[fe]);let Re=r.convert(Ce.format,Ce.colorSpace),ae=r.convert(Ce.type),we=M(Ce.internalFormat,Re,ae,Ce.colorSpace,S.isXRRenderTarget===!0),Be=pe(S);n.renderbufferStorageMultisample(n.RENDERBUFFER,Be,we,S.width,S.height),n.framebufferRenderbuffer(n.FRAMEBUFFER,n.COLOR_ATTACHMENT0+fe,n.RENDERBUFFER,O.__webglColorRenderbuffer[fe])}n.bindRenderbuffer(n.RENDERBUFFER,null),S.depthBuffer&&(O.__webglDepthRenderbuffer=n.createRenderbuffer(),Ue(O.__webglDepthRenderbuffer,S,!0)),t.bindFramebuffer(n.FRAMEBUFFER,null)}}if(W){t.bindTexture(n.TEXTURE_CUBE_MAP,H.__webglTexture),ze(n.TEXTURE_CUBE_MAP,_);for(let fe=0;fe<6;fe++)if(_.mipmaps&&_.mipmaps.length>0)for(let Ce=0;Ce<_.mipmaps.length;Ce++)Me(O.__webglFramebuffer[fe][Ce],S,_,n.COLOR_ATTACHMENT0,n.TEXTURE_CUBE_MAP_POSITIVE_X+fe,Ce);else Me(O.__webglFramebuffer[fe],S,_,n.COLOR_ATTACHMENT0,n.TEXTURE_CUBE_MAP_POSITIVE_X+fe,0);m(_)&&p(n.TEXTURE_CUBE_MAP),t.unbindTexture()}else if(Ne){for(let fe=0,Ce=ee.length;fe<Ce;fe++){let Re=ee[fe],ae=i.get(Re),we=n.TEXTURE_2D;(S.isWebGL3DRenderTarget||S.isWebGLArrayRenderTarget)&&(we=S.isWebGL3DRenderTarget?n.TEXTURE_3D:n.TEXTURE_2D_ARRAY),t.bindTexture(we,ae.__webglTexture),ze(we,Re),Me(O.__webglFramebuffer,S,Re,n.COLOR_ATTACHMENT0+fe,we,0),m(Re)&&p(we)}t.unbindTexture()}else{let fe=n.TEXTURE_2D;if((S.isWebGL3DRenderTarget||S.isWebGLArrayRenderTarget)&&(fe=S.isWebGL3DRenderTarget?n.TEXTURE_3D:n.TEXTURE_2D_ARRAY),t.bindTexture(fe,H.__webglTexture),ze(fe,_),_.mipmaps&&_.mipmaps.length>0)for(let Ce=0;Ce<_.mipmaps.length;Ce++)Me(O.__webglFramebuffer[Ce],S,_,n.COLOR_ATTACHMENT0,fe,Ce);else Me(O.__webglFramebuffer,S,_,n.COLOR_ATTACHMENT0,fe,0);m(_)&&p(fe),t.unbindTexture()}S.depthBuffer&&et(S)}function ne(S){let _=S.textures;for(let O=0,H=_.length;O<H;O++){let ee=_[O];if(m(ee)){let W=T(S),Ne=i.get(ee).__webglTexture;t.bindTexture(W,Ne),p(W),t.unbindTexture()}}}let J=[],Z=[];function $(S){if(S.samples>0){if(re(S)===!1){let _=S.textures,O=S.width,H=S.height,ee=n.COLOR_BUFFER_BIT,W=S.stencilBuffer?n.DEPTH_STENCIL_ATTACHMENT:n.DEPTH_ATTACHMENT,Ne=i.get(S),fe=_.length>1;if(fe)for(let Re=0;Re<_.length;Re++)t.bindFramebuffer(n.FRAMEBUFFER,Ne.__webglMultisampledFramebuffer),n.framebufferRenderbuffer(n.FRAMEBUFFER,n.COLOR_ATTACHMENT0+Re,n.RENDERBUFFER,null),t.bindFramebuffer(n.FRAMEBUFFER,Ne.__webglFramebuffer),n.framebufferTexture2D(n.DRAW_FRAMEBUFFER,n.COLOR_ATTACHMENT0+Re,n.TEXTURE_2D,null,0);t.bindFramebuffer(n.READ_FRAMEBUFFER,Ne.__webglMultisampledFramebuffer);let Ce=S.texture.mipmaps;Ce&&Ce.length>0?t.bindFramebuffer(n.DRAW_FRAMEBUFFER,Ne.__webglFramebuffer[0]):t.bindFramebuffer(n.DRAW_FRAMEBUFFER,Ne.__webglFramebuffer);for(let Re=0;Re<_.length;Re++){if(S.resolveDepthBuffer&&(S.depthBuffer&&(ee|=n.DEPTH_BUFFER_BIT),S.stencilBuffer&&S.resolveStencilBuffer&&(ee|=n.STENCIL_BUFFER_BIT)),fe){n.framebufferRenderbuffer(n.READ_FRAMEBUFFER,n.COLOR_ATTACHMENT0,n.RENDERBUFFER,Ne.__webglColorRenderbuffer[Re]);let ae=i.get(_[Re]).__webglTexture;n.framebufferTexture2D(n.DRAW_FRAMEBUFFER,n.COLOR_ATTACHMENT0,n.TEXTURE_2D,ae,0)}n.blitFramebuffer(0,0,O,H,0,0,O,H,ee,n.NEAREST),c===!0&&(J.length=0,Z.length=0,J.push(n.COLOR_ATTACHMENT0+Re),S.depthBuffer&&S.resolveDepthBuffer===!1&&(J.push(W),Z.push(W),n.invalidateFramebuffer(n.DRAW_FRAMEBUFFER,Z)),n.invalidateFramebuffer(n.READ_FRAMEBUFFER,J))}if(t.bindFramebuffer(n.READ_FRAMEBUFFER,null),t.bindFramebuffer(n.DRAW_FRAMEBUFFER,null),fe)for(let Re=0;Re<_.length;Re++){t.bindFramebuffer(n.FRAMEBUFFER,Ne.__webglMultisampledFramebuffer),n.framebufferRenderbuffer(n.FRAMEBUFFER,n.COLOR_ATTACHMENT0+Re,n.RENDERBUFFER,Ne.__webglColorRenderbuffer[Re]);let ae=i.get(_[Re]).__webglTexture;t.bindFramebuffer(n.FRAMEBUFFER,Ne.__webglFramebuffer),n.framebufferTexture2D(n.DRAW_FRAMEBUFFER,n.COLOR_ATTACHMENT0+Re,n.TEXTURE_2D,ae,0)}t.bindFramebuffer(n.DRAW_FRAMEBUFFER,Ne.__webglMultisampledFramebuffer)}else if(S.depthBuffer&&S.resolveDepthBuffer===!1&&c){let _=S.stencilBuffer?n.DEPTH_STENCIL_ATTACHMENT:n.DEPTH_ATTACHMENT;n.invalidateFramebuffer(n.DRAW_FRAMEBUFFER,[_])}}}function pe(S){return Math.min(s.maxSamples,S.samples)}function re(S){let _=i.get(S);return S.samples>0&&e.has("WEBGL_multisampled_render_to_texture")===!0&&_.__useRenderToTexture!==!1}function me(S){let _=a.render.frame;u.get(S)!==_&&(u.set(S,_),S.update())}function We(S,_){let O=S.colorSpace,H=S.format,ee=S.type;return S.isCompressedTexture===!0||S.isVideoTexture===!0||O!==Ri&&O!==Yn&&(st.getTransfer(O)===ot?(H!==hn||ee!==vn)&&console.warn("THREE.WebGLTextures: sRGB encoded textures have to use RGBAFormat and UnsignedByteType."):console.error("THREE.WebGLTextures: Unsupported texture color space:",O)),_}function He(S){return typeof HTMLImageElement<"u"&&S instanceof HTMLImageElement?(l.width=S.naturalWidth||S.width,l.height=S.naturalHeight||S.height):typeof VideoFrame<"u"&&S instanceof VideoFrame?(l.width=S.displayWidth,l.height=S.displayHeight):(l.width=S.width,l.height=S.height),l}this.allocateTextureUnit=G,this.resetTextureUnits=k,this.setTexture2D=X,this.setTexture2DArray=V,this.setTexture3D=te,this.setTextureCube=U,this.rebindTextures=ft,this.setupRenderTarget=A,this.updateRenderTargetMipmap=ne,this.updateMultisampleRenderTarget=$,this.setupDepthRenderbuffer=et,this.setupFrameBufferTexture=Me,this.useMultisampledRTT=re}function p0(n,e){function t(i,s=Yn){let r,a=st.getTransfer(s);if(i===vn)return n.UNSIGNED_BYTE;if(i===Ja)return n.UNSIGNED_SHORT_4_4_4_4;if(i===Ka)return n.UNSIGNED_SHORT_5_5_5_1;if(i===Yl)return n.UNSIGNED_INT_5_9_9_9_REV;if(i===$l)return n.UNSIGNED_INT_10F_11F_11F_REV;if(i===Xl)return n.BYTE;if(i===ql)return n.SHORT;if(i===vs)return n.UNSIGNED_SHORT;if(i===Za)return n.INT;if(i===mi)return n.UNSIGNED_INT;if(i===Cn)return n.FLOAT;if(i===ys)return n.HALF_FLOAT;if(i===Zl)return n.ALPHA;if(i===Jl)return n.RGB;if(i===hn)return n.RGBA;if(i===ls)return n.DEPTH_COMPONENT;if(i===bs)return n.DEPTH_STENCIL;if(i===Kl)return n.RED;if(i===ja)return n.RED_INTEGER;if(i===jl)return n.RG;if(i===Qa)return n.RG_INTEGER;if(i===eo)return n.RGBA_INTEGER;if(i===Tr||i===Er||i===Ar||i===Cr)if(a===ot)if(r=e.get("WEBGL_compressed_texture_s3tc_srgb"),r!==null){if(i===Tr)return r.COMPRESSED_SRGB_S3TC_DXT1_EXT;if(i===Er)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT1_EXT;if(i===Ar)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT3_EXT;if(i===Cr)return r.COMPRESSED_SRGB_ALPHA_S3TC_DXT5_EXT}else return null;else if(r=e.get("WEBGL_compressed_texture_s3tc"),r!==null){if(i===Tr)return r.COMPRESSED_RGB_S3TC_DXT1_EXT;if(i===Er)return r.COMPRESSED_RGBA_S3TC_DXT1_EXT;if(i===Ar)return r.COMPRESSED_RGBA_S3TC_DXT3_EXT;if(i===Cr)return r.COMPRESSED_RGBA_S3TC_DXT5_EXT}else return null;if(i===to||i===no||i===io||i===so)if(r=e.get("WEBGL_compressed_texture_pvrtc"),r!==null){if(i===to)return r.COMPRESSED_RGB_PVRTC_4BPPV1_IMG;if(i===no)return r.COMPRESSED_RGB_PVRTC_2BPPV1_IMG;if(i===io)return r.COMPRESSED_RGBA_PVRTC_4BPPV1_IMG;if(i===so)return r.COMPRESSED_RGBA_PVRTC_2BPPV1_IMG}else return null;if(i===ro||i===ao||i===oo)if(r=e.get("WEBGL_compressed_texture_etc"),r!==null){if(i===ro||i===ao)return a===ot?r.COMPRESSED_SRGB8_ETC2:r.COMPRESSED_RGB8_ETC2;if(i===oo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ETC2_EAC:r.COMPRESSED_RGBA8_ETC2_EAC}else return null;if(i===lo||i===co||i===ho||i===uo||i===fo||i===po||i===mo||i===go||i===_o||i===xo||i===vo||i===yo||i===wo||i===bo)if(r=e.get("WEBGL_compressed_texture_astc"),r!==null){if(i===lo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_4x4_KHR:r.COMPRESSED_RGBA_ASTC_4x4_KHR;if(i===co)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x4_KHR:r.COMPRESSED_RGBA_ASTC_5x4_KHR;if(i===ho)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_5x5_KHR:r.COMPRESSED_RGBA_ASTC_5x5_KHR;if(i===uo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x5_KHR:r.COMPRESSED_RGBA_ASTC_6x5_KHR;if(i===fo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_6x6_KHR:r.COMPRESSED_RGBA_ASTC_6x6_KHR;if(i===po)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x5_KHR:r.COMPRESSED_RGBA_ASTC_8x5_KHR;if(i===mo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x6_KHR:r.COMPRESSED_RGBA_ASTC_8x6_KHR;if(i===go)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_8x8_KHR:r.COMPRESSED_RGBA_ASTC_8x8_KHR;if(i===_o)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x5_KHR:r.COMPRESSED_RGBA_ASTC_10x5_KHR;if(i===xo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x6_KHR:r.COMPRESSED_RGBA_ASTC_10x6_KHR;if(i===vo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x8_KHR:r.COMPRESSED_RGBA_ASTC_10x8_KHR;if(i===yo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_10x10_KHR:r.COMPRESSED_RGBA_ASTC_10x10_KHR;if(i===wo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x10_KHR:r.COMPRESSED_RGBA_ASTC_12x10_KHR;if(i===bo)return a===ot?r.COMPRESSED_SRGB8_ALPHA8_ASTC_12x12_KHR:r.COMPRESSED_RGBA_ASTC_12x12_KHR}else return null;if(i===Mo||i===So||i===To)if(r=e.get("EXT_texture_compression_bptc"),r!==null){if(i===Mo)return a===ot?r.COMPRESSED_SRGB_ALPHA_BPTC_UNORM_EXT:r.COMPRESSED_RGBA_BPTC_UNORM_EXT;if(i===So)return r.COMPRESSED_RGB_BPTC_SIGNED_FLOAT_EXT;if(i===To)return r.COMPRESSED_RGB_BPTC_UNSIGNED_FLOAT_EXT}else return null;if(i===Eo||i===Ao||i===Co||i===Ro)if(r=e.get("EXT_texture_compression_rgtc"),r!==null){if(i===Eo)return r.COMPRESSED_RED_RGTC1_EXT;if(i===Ao)return r.COMPRESSED_SIGNED_RED_RGTC1_EXT;if(i===Co)return r.COMPRESSED_RED_GREEN_RGTC2_EXT;if(i===Ro)return r.COMPRESSED_SIGNED_RED_GREEN_RGTC2_EXT}else return null;return i===ws?n.UNSIGNED_INT_24_8:n[i]!==void 0?n[i]:null}return{convert:t}}var m0=`
void main() {

	gl_Position = vec4( position, 1.0 );

}`,g0=`
uniform sampler2DArray depthColor;
uniform float depthWidth;
uniform float depthHeight;

void main() {

	vec2 coord = vec2( gl_FragCoord.x / depthWidth, gl_FragCoord.y / depthHeight );

	if ( coord.x >= 1.0 ) {

		gl_FragDepth = texture( depthColor, vec3( coord.x - 1.0, coord.y, 1 ) ).r;

	} else {

		gl_FragDepth = texture( depthColor, vec3( coord.x, coord.y, 0 ) ).r;

	}

}`,bc=class{constructor(){this.texture=null,this.mesh=null,this.depthNear=0,this.depthFar=0}init(e,t){if(this.texture===null){let i=new ar(e.texture);(e.depthNear!==t.depthNear||e.depthFar!==t.depthFar)&&(this.depthNear=e.depthNear,this.depthFar=e.depthFar),this.texture=i}}getMesh(e){if(this.texture!==null&&this.mesh===null){let t=e.cameras[0].viewport,i=new xn({vertexShader:m0,fragmentShader:g0,uniforms:{depthColor:{value:this.texture},depthWidth:{value:t.z},depthHeight:{value:t.w}}});this.mesh=new Ot(new gr(20,20),i)}return this.mesh}reset(){this.texture=null,this.mesh=null}getDepthTexture(){return this.texture}},Mc=class extends Mn{constructor(e,t){super();let i=this,s=null,r=1,a=null,o="local-floor",c=1,l=null,u=null,h=null,d=null,f=null,g=null,x=typeof XRWebGLBinding<"u",m=new bc,p={},T=t.getContextAttributes(),M=null,y=null,R=[],E=[],P=new de,D=null,b=new Ut;b.viewport=new wt;let w=new Ut;w.viewport=new wt;let C=[b,w],k=new Oa,G=null,q=null;this.cameraAutoUpdate=!0,this.enabled=!1,this.isPresenting=!1,this.getController=function(Y){let se=R[Y];return se===void 0&&(se=new ps,R[Y]=se),se.getTargetRaySpace()},this.getControllerGrip=function(Y){let se=R[Y];return se===void 0&&(se=new ps,R[Y]=se),se.getGripSpace()},this.getHand=function(Y){let se=R[Y];return se===void 0&&(se=new ps,R[Y]=se),se.getHandSpace()};function X(Y){let se=E.indexOf(Y.inputSource);if(se===-1)return;let Me=R[se];Me!==void 0&&(Me.update(Y.inputSource,Y.frame,l||a),Me.dispatchEvent({type:Y.type,data:Y.inputSource}))}function V(){s.removeEventListener("select",X),s.removeEventListener("selectstart",X),s.removeEventListener("selectend",X),s.removeEventListener("squeeze",X),s.removeEventListener("squeezestart",X),s.removeEventListener("squeezeend",X),s.removeEventListener("end",V),s.removeEventListener("inputsourceschange",te);for(let Y=0;Y<R.length;Y++){let se=E[Y];se!==null&&(E[Y]=null,R[Y].disconnect(se))}G=null,q=null,m.reset();for(let Y in p)delete p[Y];e.setRenderTarget(M),f=null,d=null,h=null,s=null,y=null,it.stop(),i.isPresenting=!1,e.setPixelRatio(D),e.setSize(P.width,P.height,!1),i.dispatchEvent({type:"sessionend"})}this.setFramebufferScaleFactor=function(Y){r=Y,i.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change framebuffer scale while presenting.")},this.setReferenceSpaceType=function(Y){o=Y,i.isPresenting===!0&&console.warn("THREE.WebXRManager: Cannot change reference space type while presenting.")},this.getReferenceSpace=function(){return l||a},this.setReferenceSpace=function(Y){l=Y},this.getBaseLayer=function(){return d!==null?d:f},this.getBinding=function(){return h===null&&x&&(h=new XRWebGLBinding(s,t)),h},this.getFrame=function(){return g},this.getSession=function(){return s},this.setSession=async function(Y){if(s=Y,s!==null){if(M=e.getRenderTarget(),s.addEventListener("select",X),s.addEventListener("selectstart",X),s.addEventListener("selectend",X),s.addEventListener("squeeze",X),s.addEventListener("squeezestart",X),s.addEventListener("squeezeend",X),s.addEventListener("end",V),s.addEventListener("inputsourceschange",te),T.xrCompatible!==!0&&await t.makeXRCompatible(),D=e.getPixelRatio(),e.getSize(P),x&&"createProjectionLayer"in XRWebGLBinding.prototype){let Me=null,Ue=null,Ae=null;T.depth&&(Ae=T.stencil?t.DEPTH24_STENCIL8:t.DEPTH_COMPONENT24,Me=T.stencil?bs:ls,Ue=T.stencil?ws:mi);let et={colorFormat:t.RGBA8,depthFormat:Ae,scaleFactor:r};h=this.getBinding(),d=h.createProjectionLayer(et),s.updateRenderState({layers:[d]}),e.setPixelRatio(1),e.setSize(d.textureWidth,d.textureHeight,!1),y=new Sn(d.textureWidth,d.textureHeight,{format:hn,type:vn,depthTexture:new rr(d.textureWidth,d.textureHeight,Ue,void 0,void 0,void 0,void 0,void 0,void 0,Me),stencilBuffer:T.stencil,colorSpace:e.outputColorSpace,samples:T.antialias?4:0,resolveDepthBuffer:d.ignoreDepthValues===!1,resolveStencilBuffer:d.ignoreDepthValues===!1})}else{let Me={antialias:T.antialias,alpha:!0,depth:T.depth,stencil:T.stencil,framebufferScaleFactor:r};f=new XRWebGLLayer(s,t,Me),s.updateRenderState({baseLayer:f}),e.setPixelRatio(1),e.setSize(f.framebufferWidth,f.framebufferHeight,!1),y=new Sn(f.framebufferWidth,f.framebufferHeight,{format:hn,type:vn,colorSpace:e.outputColorSpace,stencilBuffer:T.stencil,resolveDepthBuffer:f.ignoreDepthValues===!1,resolveStencilBuffer:f.ignoreDepthValues===!1})}y.isXRRenderTarget=!0,this.setFoveation(c),l=null,a=await s.requestReferenceSpace(o),it.setContext(s),it.start(),i.isPresenting=!0,i.dispatchEvent({type:"sessionstart"})}},this.getEnvironmentBlendMode=function(){if(s!==null)return s.environmentBlendMode},this.getDepthTexture=function(){return m.getDepthTexture()};function te(Y){for(let se=0;se<Y.removed.length;se++){let Me=Y.removed[se],Ue=E.indexOf(Me);Ue>=0&&(E[Ue]=null,R[Ue].disconnect(Me))}for(let se=0;se<Y.added.length;se++){let Me=Y.added[se],Ue=E.indexOf(Me);if(Ue===-1){for(let et=0;et<R.length;et++)if(et>=E.length){E.push(Me),Ue=et;break}else if(E[et]===null){E[et]=Me,Ue=et;break}if(Ue===-1)break}let Ae=R[Ue];Ae&&Ae.connect(Me)}}let U=new N,Q=new N;function he(Y,se,Me){U.setFromMatrixPosition(se.matrixWorld),Q.setFromMatrixPosition(Me.matrixWorld);let Ue=U.distanceTo(Q),Ae=se.projectionMatrix.elements,et=Me.projectionMatrix.elements,ft=Ae[14]/(Ae[10]-1),A=Ae[14]/(Ae[10]+1),ne=(Ae[9]+1)/Ae[5],J=(Ae[9]-1)/Ae[5],Z=(Ae[8]-1)/Ae[0],$=(et[8]+1)/et[0],pe=ft*Z,re=ft*$,me=Ue/(-Z+$),We=me*-Z;if(se.matrixWorld.decompose(Y.position,Y.quaternion,Y.scale),Y.translateX(We),Y.translateZ(me),Y.matrixWorld.compose(Y.position,Y.quaternion,Y.scale),Y.matrixWorldInverse.copy(Y.matrixWorld).invert(),Ae[10]===-1)Y.projectionMatrix.copy(se.projectionMatrix),Y.projectionMatrixInverse.copy(se.projectionMatrixInverse);else{let He=ft+me,S=A+me,_=pe-We,O=re+(Ue-We),H=ne*A/S*He,ee=J*A/S*He;Y.projectionMatrix.makePerspective(_,O,H,ee,He,S),Y.projectionMatrixInverse.copy(Y.projectionMatrix).invert()}}function ue(Y,se){se===null?Y.matrixWorld.copy(Y.matrix):Y.matrixWorld.multiplyMatrices(se.matrixWorld,Y.matrix),Y.matrixWorldInverse.copy(Y.matrixWorld).invert()}this.updateCamera=function(Y){if(s===null)return;let se=Y.near,Me=Y.far;m.texture!==null&&(m.depthNear>0&&(se=m.depthNear),m.depthFar>0&&(Me=m.depthFar)),k.near=w.near=b.near=se,k.far=w.far=b.far=Me,(G!==k.near||q!==k.far)&&(s.updateRenderState({depthNear:k.near,depthFar:k.far}),G=k.near,q=k.far),k.layers.mask=Y.layers.mask|6,b.layers.mask=k.layers.mask&3,w.layers.mask=k.layers.mask&5;let Ue=Y.parent,Ae=k.cameras;ue(k,Ue);for(let et=0;et<Ae.length;et++)ue(Ae[et],Ue);Ae.length===2?he(k,b,w):k.projectionMatrix.copy(b.projectionMatrix),ze(Y,k,Ue)};function ze(Y,se,Me){Me===null?Y.matrix.copy(se.matrixWorld):(Y.matrix.copy(Me.matrixWorld),Y.matrix.invert(),Y.matrix.multiply(se.matrixWorld)),Y.matrix.decompose(Y.position,Y.quaternion,Y.scale),Y.updateMatrixWorld(!0),Y.projectionMatrix.copy(se.projectionMatrix),Y.projectionMatrixInverse.copy(se.projectionMatrixInverse),Y.isPerspectiveCamera&&(Y.fov=cs*2*Math.atan(1/Y.projectionMatrix.elements[5]),Y.zoom=1)}this.getCamera=function(){return k},this.getFoveation=function(){if(!(d===null&&f===null))return c},this.setFoveation=function(Y){c=Y,d!==null&&(d.fixedFoveation=Y),f!==null&&f.fixedFoveation!==void 0&&(f.fixedFoveation=Y)},this.hasDepthSensing=function(){return m.texture!==null},this.getDepthSensingMesh=function(){return m.getMesh(k)},this.getCameraTexture=function(Y){return p[Y]};let je=null;function Qe(Y,se){if(u=se.getViewerPose(l||a),g=se,u!==null){let Me=u.views;f!==null&&(e.setRenderTargetFramebuffer(y,f.framebuffer),e.setRenderTarget(y));let Ue=!1;Me.length!==k.cameras.length&&(k.cameras.length=0,Ue=!0);for(let A=0;A<Me.length;A++){let ne=Me[A],J=null;if(f!==null)J=f.getViewport(ne);else{let $=h.getViewSubImage(d,ne);J=$.viewport,A===0&&(e.setRenderTargetTextures(y,$.colorTexture,$.depthStencilTexture),e.setRenderTarget(y))}let Z=C[A];Z===void 0&&(Z=new Ut,Z.layers.enable(A),Z.viewport=new wt,C[A]=Z),Z.matrix.fromArray(ne.transform.matrix),Z.matrix.decompose(Z.position,Z.quaternion,Z.scale),Z.projectionMatrix.fromArray(ne.projectionMatrix),Z.projectionMatrixInverse.copy(Z.projectionMatrix).invert(),Z.viewport.set(J.x,J.y,J.width,J.height),A===0&&(k.matrix.copy(Z.matrix),k.matrix.decompose(k.position,k.quaternion,k.scale)),Ue===!0&&k.cameras.push(Z)}let Ae=s.enabledFeatures;if(Ae&&Ae.includes("depth-sensing")&&s.depthUsage=="gpu-optimized"&&x){h=i.getBinding();let A=h.getDepthInformation(Me[0]);A&&A.isValid&&A.texture&&m.init(A,s.renderState)}if(Ae&&Ae.includes("camera-access")&&x){e.state.unbindTexture(),h=i.getBinding();for(let A=0;A<Me.length;A++){let ne=Me[A].camera;if(ne){let J=p[ne];J||(J=new ar,p[ne]=J);let Z=h.getCameraImage(ne);J.sourceTexture=Z}}}}for(let Me=0;Me<R.length;Me++){let Ue=E[Me],Ae=R[Me];Ue!==null&&Ae!==void 0&&Ae.update(Ue,se,l||a)}je&&je(Y,se),se.detectedPlanes&&i.dispatchEvent({type:"planesdetected",data:se}),g=null}let it=new ud;it.setAnimationLoop(Qe),this.setAnimationLoop=function(Y){je=Y},this.dispose=function(){}}},Bi=new _n,_0=new Mt;function x0(n,e){function t(m,p){m.matrixAutoUpdate===!0&&m.updateMatrix(),p.value.copy(m.matrix)}function i(m,p){p.color.getRGB(m.fogColor.value,rc(n)),p.isFog?(m.fogNear.value=p.near,m.fogFar.value=p.far):p.isFogExp2&&(m.fogDensity.value=p.density)}function s(m,p,T,M,y){p.isMeshBasicMaterial||p.isMeshLambertMaterial?r(m,p):p.isMeshToonMaterial?(r(m,p),h(m,p)):p.isMeshPhongMaterial?(r(m,p),u(m,p)):p.isMeshStandardMaterial?(r(m,p),d(m,p),p.isMeshPhysicalMaterial&&f(m,p,y)):p.isMeshMatcapMaterial?(r(m,p),g(m,p)):p.isMeshDepthMaterial?r(m,p):p.isMeshDistanceMaterial?(r(m,p),x(m,p)):p.isMeshNormalMaterial?r(m,p):p.isLineBasicMaterial?(a(m,p),p.isLineDashedMaterial&&o(m,p)):p.isPointsMaterial?c(m,p,T,M):p.isSpriteMaterial?l(m,p):p.isShadowMaterial?(m.color.value.copy(p.color),m.opacity.value=p.opacity):p.isShaderMaterial&&(p.uniformsNeedUpdate=!1)}function r(m,p){m.opacity.value=p.opacity,p.color&&m.diffuse.value.copy(p.color),p.emissive&&m.emissive.value.copy(p.emissive).multiplyScalar(p.emissiveIntensity),p.map&&(m.map.value=p.map,t(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.bumpMap&&(m.bumpMap.value=p.bumpMap,t(p.bumpMap,m.bumpMapTransform),m.bumpScale.value=p.bumpScale,p.side===Wt&&(m.bumpScale.value*=-1)),p.normalMap&&(m.normalMap.value=p.normalMap,t(p.normalMap,m.normalMapTransform),m.normalScale.value.copy(p.normalScale),p.side===Wt&&m.normalScale.value.negate()),p.displacementMap&&(m.displacementMap.value=p.displacementMap,t(p.displacementMap,m.displacementMapTransform),m.displacementScale.value=p.displacementScale,m.displacementBias.value=p.displacementBias),p.emissiveMap&&(m.emissiveMap.value=p.emissiveMap,t(p.emissiveMap,m.emissiveMapTransform)),p.specularMap&&(m.specularMap.value=p.specularMap,t(p.specularMap,m.specularMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest);let T=e.get(p),M=T.envMap,y=T.envMapRotation;M&&(m.envMap.value=M,Bi.copy(y),Bi.x*=-1,Bi.y*=-1,Bi.z*=-1,M.isCubeTexture&&M.isRenderTargetTexture===!1&&(Bi.y*=-1,Bi.z*=-1),m.envMapRotation.value.setFromMatrix4(_0.makeRotationFromEuler(Bi)),m.flipEnvMap.value=M.isCubeTexture&&M.isRenderTargetTexture===!1?-1:1,m.reflectivity.value=p.reflectivity,m.ior.value=p.ior,m.refractionRatio.value=p.refractionRatio),p.lightMap&&(m.lightMap.value=p.lightMap,m.lightMapIntensity.value=p.lightMapIntensity,t(p.lightMap,m.lightMapTransform)),p.aoMap&&(m.aoMap.value=p.aoMap,m.aoMapIntensity.value=p.aoMapIntensity,t(p.aoMap,m.aoMapTransform))}function a(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,p.map&&(m.map.value=p.map,t(p.map,m.mapTransform))}function o(m,p){m.dashSize.value=p.dashSize,m.totalSize.value=p.dashSize+p.gapSize,m.scale.value=p.scale}function c(m,p,T,M){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.size.value=p.size*T,m.scale.value=M*.5,p.map&&(m.map.value=p.map,t(p.map,m.uvTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function l(m,p){m.diffuse.value.copy(p.color),m.opacity.value=p.opacity,m.rotation.value=p.rotation,p.map&&(m.map.value=p.map,t(p.map,m.mapTransform)),p.alphaMap&&(m.alphaMap.value=p.alphaMap,t(p.alphaMap,m.alphaMapTransform)),p.alphaTest>0&&(m.alphaTest.value=p.alphaTest)}function u(m,p){m.specular.value.copy(p.specular),m.shininess.value=Math.max(p.shininess,1e-4)}function h(m,p){p.gradientMap&&(m.gradientMap.value=p.gradientMap)}function d(m,p){m.metalness.value=p.metalness,p.metalnessMap&&(m.metalnessMap.value=p.metalnessMap,t(p.metalnessMap,m.metalnessMapTransform)),m.roughness.value=p.roughness,p.roughnessMap&&(m.roughnessMap.value=p.roughnessMap,t(p.roughnessMap,m.roughnessMapTransform)),p.envMap&&(m.envMapIntensity.value=p.envMapIntensity)}function f(m,p,T){m.ior.value=p.ior,p.sheen>0&&(m.sheenColor.value.copy(p.sheenColor).multiplyScalar(p.sheen),m.sheenRoughness.value=p.sheenRoughness,p.sheenColorMap&&(m.sheenColorMap.value=p.sheenColorMap,t(p.sheenColorMap,m.sheenColorMapTransform)),p.sheenRoughnessMap&&(m.sheenRoughnessMap.value=p.sheenRoughnessMap,t(p.sheenRoughnessMap,m.sheenRoughnessMapTransform))),p.clearcoat>0&&(m.clearcoat.value=p.clearcoat,m.clearcoatRoughness.value=p.clearcoatRoughness,p.clearcoatMap&&(m.clearcoatMap.value=p.clearcoatMap,t(p.clearcoatMap,m.clearcoatMapTransform)),p.clearcoatRoughnessMap&&(m.clearcoatRoughnessMap.value=p.clearcoatRoughnessMap,t(p.clearcoatRoughnessMap,m.clearcoatRoughnessMapTransform)),p.clearcoatNormalMap&&(m.clearcoatNormalMap.value=p.clearcoatNormalMap,t(p.clearcoatNormalMap,m.clearcoatNormalMapTransform),m.clearcoatNormalScale.value.copy(p.clearcoatNormalScale),p.side===Wt&&m.clearcoatNormalScale.value.negate())),p.dispersion>0&&(m.dispersion.value=p.dispersion),p.iridescence>0&&(m.iridescence.value=p.iridescence,m.iridescenceIOR.value=p.iridescenceIOR,m.iridescenceThicknessMinimum.value=p.iridescenceThicknessRange[0],m.iridescenceThicknessMaximum.value=p.iridescenceThicknessRange[1],p.iridescenceMap&&(m.iridescenceMap.value=p.iridescenceMap,t(p.iridescenceMap,m.iridescenceMapTransform)),p.iridescenceThicknessMap&&(m.iridescenceThicknessMap.value=p.iridescenceThicknessMap,t(p.iridescenceThicknessMap,m.iridescenceThicknessMapTransform))),p.transmission>0&&(m.transmission.value=p.transmission,m.transmissionSamplerMap.value=T.texture,m.transmissionSamplerSize.value.set(T.width,T.height),p.transmissionMap&&(m.transmissionMap.value=p.transmissionMap,t(p.transmissionMap,m.transmissionMapTransform)),m.thickness.value=p.thickness,p.thicknessMap&&(m.thicknessMap.value=p.thicknessMap,t(p.thicknessMap,m.thicknessMapTransform)),m.attenuationDistance.value=p.attenuationDistance,m.attenuationColor.value.copy(p.attenuationColor)),p.anisotropy>0&&(m.anisotropyVector.value.set(p.anisotropy*Math.cos(p.anisotropyRotation),p.anisotropy*Math.sin(p.anisotropyRotation)),p.anisotropyMap&&(m.anisotropyMap.value=p.anisotropyMap,t(p.anisotropyMap,m.anisotropyMapTransform))),m.specularIntensity.value=p.specularIntensity,m.specularColor.value.copy(p.specularColor),p.specularColorMap&&(m.specularColorMap.value=p.specularColorMap,t(p.specularColorMap,m.specularColorMapTransform)),p.specularIntensityMap&&(m.specularIntensityMap.value=p.specularIntensityMap,t(p.specularIntensityMap,m.specularIntensityMapTransform))}function g(m,p){p.matcap&&(m.matcap.value=p.matcap)}function x(m,p){let T=e.get(p).light;m.referencePosition.value.setFromMatrixPosition(T.matrixWorld),m.nearDistance.value=T.shadow.camera.near,m.farDistance.value=T.shadow.camera.far}return{refreshFogUniforms:i,refreshMaterialUniforms:s}}function v0(n,e,t,i){let s={},r={},a=[],o=n.getParameter(n.MAX_UNIFORM_BUFFER_BINDINGS);function c(T,M){let y=M.program;i.uniformBlockBinding(T,y)}function l(T,M){let y=s[T.id];y===void 0&&(g(T),y=u(T),s[T.id]=y,T.addEventListener("dispose",m));let R=M.program;i.updateUBOMapping(T,R);let E=e.render.frame;r[T.id]!==E&&(d(T),r[T.id]=E)}function u(T){let M=h();T.__bindingPointIndex=M;let y=n.createBuffer(),R=T.__size,E=T.usage;return n.bindBuffer(n.UNIFORM_BUFFER,y),n.bufferData(n.UNIFORM_BUFFER,R,E),n.bindBuffer(n.UNIFORM_BUFFER,null),n.bindBufferBase(n.UNIFORM_BUFFER,M,y),y}function h(){for(let T=0;T<o;T++)if(a.indexOf(T)===-1)return a.push(T),T;return console.error("THREE.WebGLRenderer: Maximum number of simultaneously usable uniforms groups reached."),0}function d(T){let M=s[T.id],y=T.uniforms,R=T.__cache;n.bindBuffer(n.UNIFORM_BUFFER,M);for(let E=0,P=y.length;E<P;E++){let D=Array.isArray(y[E])?y[E]:[y[E]];for(let b=0,w=D.length;b<w;b++){let C=D[b];if(f(C,E,b,R)===!0){let k=C.__offset,G=Array.isArray(C.value)?C.value:[C.value],q=0;for(let X=0;X<G.length;X++){let V=G[X],te=x(V);typeof V=="number"||typeof V=="boolean"?(C.__data[0]=V,n.bufferSubData(n.UNIFORM_BUFFER,k+q,C.__data)):V.isMatrix3?(C.__data[0]=V.elements[0],C.__data[1]=V.elements[1],C.__data[2]=V.elements[2],C.__data[3]=0,C.__data[4]=V.elements[3],C.__data[5]=V.elements[4],C.__data[6]=V.elements[5],C.__data[7]=0,C.__data[8]=V.elements[6],C.__data[9]=V.elements[7],C.__data[10]=V.elements[8],C.__data[11]=0):(V.toArray(C.__data,q),q+=te.storage/Float32Array.BYTES_PER_ELEMENT)}n.bufferSubData(n.UNIFORM_BUFFER,k,C.__data)}}}n.bindBuffer(n.UNIFORM_BUFFER,null)}function f(T,M,y,R){let E=T.value,P=M+"_"+y;if(R[P]===void 0)return typeof E=="number"||typeof E=="boolean"?R[P]=E:R[P]=E.clone(),!0;{let D=R[P];if(typeof E=="number"||typeof E=="boolean"){if(D!==E)return R[P]=E,!0}else if(D.equals(E)===!1)return D.copy(E),!0}return!1}function g(T){let M=T.uniforms,y=0,R=16;for(let P=0,D=M.length;P<D;P++){let b=Array.isArray(M[P])?M[P]:[M[P]];for(let w=0,C=b.length;w<C;w++){let k=b[w],G=Array.isArray(k.value)?k.value:[k.value];for(let q=0,X=G.length;q<X;q++){let V=G[q],te=x(V),U=y%R,Q=U%te.boundary,he=U+Q;y+=Q,he!==0&&R-he<te.storage&&(y+=R-he),k.__data=new Float32Array(te.storage/Float32Array.BYTES_PER_ELEMENT),k.__offset=y,y+=te.storage}}}let E=y%R;return E>0&&(y+=R-E),T.__size=y,T.__cache={},this}function x(T){let M={boundary:0,storage:0};return typeof T=="number"||typeof T=="boolean"?(M.boundary=4,M.storage=4):T.isVector2?(M.boundary=8,M.storage=8):T.isVector3||T.isColor?(M.boundary=16,M.storage=12):T.isVector4?(M.boundary=16,M.storage=16):T.isMatrix3?(M.boundary=48,M.storage=48):T.isMatrix4?(M.boundary=64,M.storage=64):T.isTexture?console.warn("THREE.WebGLRenderer: Texture samplers can not be part of an uniforms group."):console.warn("THREE.WebGLRenderer: Unsupported uniform value type.",T),M}function m(T){let M=T.target;M.removeEventListener("dispose",m);let y=a.indexOf(M.__bindingPointIndex);a.splice(y,1),n.deleteBuffer(s[M.id]),delete s[M.id],delete r[M.id]}function p(){for(let T in s)n.deleteBuffer(s[T]);a=[],s={},r={}}return{bind:c,update:l,dispose:p}}var Lo=class{constructor(e={}){let{canvas:t=Du(),context:i=null,depth:s=!0,stencil:r=!1,alpha:a=!1,antialias:o=!1,premultipliedAlpha:c=!0,preserveDrawingBuffer:l=!1,powerPreference:u="default",failIfMajorPerformanceCaveat:h=!1,reversedDepthBuffer:d=!1}=e;this.isWebGLRenderer=!0;let f;if(i!==null){if(typeof WebGLRenderingContext<"u"&&i instanceof WebGLRenderingContext)throw new Error("THREE.WebGLRenderer: WebGL 1 is not supported since r163.");f=i.getContextAttributes().alpha}else f=a;let g=new Uint32Array(4),x=new Int32Array(4),m=null,p=null,T=[],M=[];this.domElement=t,this.debug={checkShaderErrors:!0,onShaderError:null},this.autoClear=!0,this.autoClearColor=!0,this.autoClearDepth=!0,this.autoClearStencil=!0,this.sortObjects=!0,this.clippingPlanes=[],this.localClippingEnabled=!1,this.toneMapping=qn,this.toneMappingExposure=1,this.transmissionResolutionScale=1;let y=this,R=!1;this._outputColorSpace=It;let E=0,P=0,D=null,b=-1,w=null,C=new wt,k=new wt,G=null,q=new qe(0),X=0,V=t.width,te=t.height,U=1,Q=null,he=null,ue=new wt(0,0,V,te),ze=new wt(0,0,V,te),je=!1,Qe=new ms,it=!1,Y=!1,se=new Mt,Me=new N,Ue=new wt,Ae={background:null,fog:null,environment:null,overrideMaterial:null,isScene:!0},et=!1;function ft(){return D===null?U:1}let A=i;function ne(v,L){return t.getContext(v,L)}try{let v={alpha:!0,depth:s,stencil:r,antialias:o,premultipliedAlpha:c,preserveDrawingBuffer:l,powerPreference:u,failIfMajorPerformanceCaveat:h};if("setAttribute"in t&&t.setAttribute("data-engine",`three.js r${"180"}`),t.addEventListener("webglcontextlost",ge,!1),t.addEventListener("webglcontextrestored",Se,!1),t.addEventListener("webglcontextcreationerror",oe,!1),A===null){let L="webgl2";if(A=ne(L,v),A===null)throw ne(L)?new Error("Error creating WebGL context with your selected attributes."):new Error("Error creating WebGL context.")}}catch(v){throw console.error("THREE.WebGLRenderer: "+v.message),v}let J,Z,$,pe,re,me,We,He,S,_,O,H,ee,W,Ne,fe,Ce,Re,ae,we,Be,Le,ve,Ze;function I(){J=new O_(A),J.init(),Le=new p0(A,J),Z=new P_(A,J,e,Le),$=new d0(A,J),Z.reversedDepthBuffer&&d&&$.buffers.depth.setReversed(!0),pe=new z_(A),re=new Qx,me=new f0(A,J,$,re,Z,Le,pe),We=new N_(y),He=new F_(y),S=new qp(A),ve=new C_(A,S),_=new k_(A,S,pe,ve),O=new H_(A,_,S,pe),ae=new V_(A,Z,me),fe=new I_(re),H=new jx(y,We,He,J,Z,ve,fe),ee=new x0(y,re),W=new t0,Ne=new o0(J),Re=new A_(y,We,He,$,O,f,c),Ce=new h0(y,O,Z),Ze=new v0(A,pe,Z,$),we=new R_(A,J,pe),Be=new B_(A,J,pe),pe.programs=H.programs,y.capabilities=Z,y.extensions=J,y.properties=re,y.renderLists=W,y.shadowMap=Ce,y.state=$,y.info=pe}I();let ce=new Mc(y,A);this.xr=ce,this.getContext=function(){return A},this.getContextAttributes=function(){return A.getContextAttributes()},this.forceContextLoss=function(){let v=J.get("WEBGL_lose_context");v&&v.loseContext()},this.forceContextRestore=function(){let v=J.get("WEBGL_lose_context");v&&v.restoreContext()},this.getPixelRatio=function(){return U},this.setPixelRatio=function(v){v!==void 0&&(U=v,this.setSize(V,te,!1))},this.getSize=function(v){return v.set(V,te)},this.setSize=function(v,L,B=!0){if(ce.isPresenting){console.warn("THREE.WebGLRenderer: Can't change size while VR device is presenting.");return}V=v,te=L,t.width=Math.floor(v*U),t.height=Math.floor(L*U),B===!0&&(t.style.width=v+"px",t.style.height=L+"px"),this.setViewport(0,0,v,L)},this.getDrawingBufferSize=function(v){return v.set(V*U,te*U).floor()},this.setDrawingBufferSize=function(v,L,B){V=v,te=L,U=B,t.width=Math.floor(v*B),t.height=Math.floor(L*B),this.setViewport(0,0,v,L)},this.getCurrentViewport=function(v){return v.copy(C)},this.getViewport=function(v){return v.copy(ue)},this.setViewport=function(v,L,B,z){v.isVector4?ue.set(v.x,v.y,v.z,v.w):ue.set(v,L,B,z),$.viewport(C.copy(ue).multiplyScalar(U).round())},this.getScissor=function(v){return v.copy(ze)},this.setScissor=function(v,L,B,z){v.isVector4?ze.set(v.x,v.y,v.z,v.w):ze.set(v,L,B,z),$.scissor(k.copy(ze).multiplyScalar(U).round())},this.getScissorTest=function(){return je},this.setScissorTest=function(v){$.setScissorTest(je=v)},this.setOpaqueSort=function(v){Q=v},this.setTransparentSort=function(v){he=v},this.getClearColor=function(v){return v.copy(Re.getClearColor())},this.setClearColor=function(){Re.setClearColor(...arguments)},this.getClearAlpha=function(){return Re.getClearAlpha()},this.setClearAlpha=function(){Re.setClearAlpha(...arguments)},this.clear=function(v=!0,L=!0,B=!0){let z=0;if(v){let F=!1;if(D!==null){let le=D.texture.format;F=le===eo||le===Qa||le===ja}if(F){let le=D.texture.type,ye=le===vn||le===mi||le===vs||le===ws||le===Ja||le===Ka,Te=Re.getClearColor(),be=Re.getClearAlpha(),ke=Te.r,Ve=Te.g,Fe=Te.b;ye?(g[0]=ke,g[1]=Ve,g[2]=Fe,g[3]=be,A.clearBufferuiv(A.COLOR,0,g)):(x[0]=ke,x[1]=Ve,x[2]=Fe,x[3]=be,A.clearBufferiv(A.COLOR,0,x))}else z|=A.COLOR_BUFFER_BIT}L&&(z|=A.DEPTH_BUFFER_BIT),B&&(z|=A.STENCIL_BUFFER_BIT,this.state.buffers.stencil.setMask(4294967295)),A.clear(z)},this.clearColor=function(){this.clear(!0,!1,!1)},this.clearDepth=function(){this.clear(!1,!0,!1)},this.clearStencil=function(){this.clear(!1,!1,!0)},this.dispose=function(){t.removeEventListener("webglcontextlost",ge,!1),t.removeEventListener("webglcontextrestored",Se,!1),t.removeEventListener("webglcontextcreationerror",oe,!1),Re.dispose(),W.dispose(),Ne.dispose(),re.dispose(),We.dispose(),He.dispose(),O.dispose(),ve.dispose(),Ze.dispose(),H.dispose(),ce.dispose(),ce.removeEventListener("sessionstart",wn),ce.removeEventListener("sessionend",Lc),xi.stop()};function ge(v){v.preventDefault(),console.log("THREE.WebGLRenderer: Context Lost."),R=!0}function Se(){console.log("THREE.WebGLRenderer: Context Restored."),R=!1;let v=pe.autoReset,L=Ce.enabled,B=Ce.autoUpdate,z=Ce.needsUpdate,F=Ce.type;I(),pe.autoReset=v,Ce.enabled=L,Ce.autoUpdate=B,Ce.needsUpdate=z,Ce.type=F}function oe(v){console.error("THREE.WebGLRenderer: A WebGL context could not be created. Reason: ",v.statusMessage)}function K(v){let L=v.target;L.removeEventListener("dispose",K),Pe(L)}function Pe(v){Xe(v),re.remove(v)}function Xe(v){let L=re.get(v).programs;L!==void 0&&(L.forEach(function(B){H.releaseProgram(B)}),v.isShaderMaterial&&H.releaseShaderCache(v))}this.renderBufferDirect=function(v,L,B,z,F,le){L===null&&(L=Ae);let ye=F.isMesh&&F.matrixWorld.determinant()<0,Te=Xd(v,L,B,z,F);$.setMaterial(z,ye);let be=B.index,ke=1;if(z.wireframe===!0){if(be=_.getWireframeAttribute(B),be===void 0)return;ke=2}let Ve=B.drawRange,Fe=B.attributes.position,tt=Ve.start*ke,lt=(Ve.start+Ve.count)*ke;le!==null&&(tt=Math.max(tt,le.start*ke),lt=Math.min(lt,(le.start+le.count)*ke)),be!==null?(tt=Math.max(tt,0),lt=Math.min(lt,be.count)):Fe!=null&&(tt=Math.max(tt,0),lt=Math.min(lt,Fe.count));let bt=lt-tt;if(bt<0||bt===1/0)return;ve.setup(F,z,Te,B,be);let mt,dt=we;if(be!==null&&(mt=S.get(be),dt=Be,dt.setIndex(mt)),F.isMesh)z.wireframe===!0?($.setLineWidth(z.wireframeLinewidth*ft()),dt.setMode(A.LINES)):dt.setMode(A.TRIANGLES);else if(F.isLine){let Oe=z.linewidth;Oe===void 0&&(Oe=1),$.setLineWidth(Oe*ft()),F.isLineSegments?dt.setMode(A.LINES):F.isLineLoop?dt.setMode(A.LINE_LOOP):dt.setMode(A.LINE_STRIP)}else F.isPoints?dt.setMode(A.POINTS):F.isSprite&&dt.setMode(A.TRIANGLES);if(F.isBatchedMesh)if(F._multiDrawInstances!==null)hs("THREE.WebGLRenderer: renderMultiDrawInstances has been deprecated and will be removed in r184. Append to renderMultiDraw arguments and use indirection."),dt.renderMultiDrawInstances(F._multiDrawStarts,F._multiDrawCounts,F._multiDrawCount,F._multiDrawInstances);else if(J.get("WEBGL_multi_draw"))dt.renderMultiDraw(F._multiDrawStarts,F._multiDrawCounts,F._multiDrawCount);else{let Oe=F._multiDrawStarts,xt=F._multiDrawCounts,rt=F._multiDrawCount,Zt=be?S.get(be).bytesPerElement:1,Gi=re.get(z).currentProgram.getUniforms();for(let Jt=0;Jt<rt;Jt++)Gi.setValue(A,"_gl_DrawID",Jt),dt.render(Oe[Jt]/Zt,xt[Jt])}else if(F.isInstancedMesh)dt.renderInstances(tt,bt,F.count);else if(B.isInstancedBufferGeometry){let Oe=B._maxInstanceCount!==void 0?B._maxInstanceCount:1/0,xt=Math.min(B.instanceCount,Oe);dt.renderInstances(tt,bt,xt)}else dt.render(tt,bt)};function pt(v,L,B){v.transparent===!0&&v.side===An&&v.forceSinglePass===!1?(v.side=Wt,v.needsUpdate=!0,Dr(v,L,B),v.side=Wn,v.needsUpdate=!0,Dr(v,L,B),v.side=An):Dr(v,L,B)}this.compile=function(v,L,B=null){B===null&&(B=v),p=Ne.get(B),p.init(L),M.push(p),B.traverseVisible(function(F){F.isLight&&F.layers.test(L.layers)&&(p.pushLight(F),F.castShadow&&p.pushShadow(F))}),v!==B&&v.traverseVisible(function(F){F.isLight&&F.layers.test(L.layers)&&(p.pushLight(F),F.castShadow&&p.pushShadow(F))}),p.setupLights();let z=new Set;return v.traverse(function(F){if(!(F.isMesh||F.isPoints||F.isLine||F.isSprite))return;let le=F.material;if(le)if(Array.isArray(le))for(let ye=0;ye<le.length;ye++){let Te=le[ye];pt(Te,B,F),z.add(Te)}else pt(le,B,F),z.add(le)}),p=M.pop(),z},this.compileAsync=function(v,L,B=null){let z=this.compile(v,L,B);return new Promise(F=>{function le(){if(z.forEach(function(ye){re.get(ye).currentProgram.isReady()&&z.delete(ye)}),z.size===0){F(v);return}setTimeout(le,10)}J.get("KHR_parallel_shader_compile")!==null?le():setTimeout(le,10)})};let at=null;function In(v){at&&at(v)}function wn(){xi.stop()}function Lc(){xi.start()}let xi=new ud;xi.setAnimationLoop(In),typeof self<"u"&&xi.setContext(self),this.setAnimationLoop=function(v){at=v,ce.setAnimationLoop(v),v===null?xi.stop():xi.start()},ce.addEventListener("sessionstart",wn),ce.addEventListener("sessionend",Lc),this.render=function(v,L){if(L!==void 0&&L.isCamera!==!0){console.error("THREE.WebGLRenderer.render: camera is not an instance of THREE.Camera.");return}if(R===!0)return;if(v.matrixWorldAutoUpdate===!0&&v.updateMatrixWorld(),L.parent===null&&L.matrixWorldAutoUpdate===!0&&L.updateMatrixWorld(),ce.enabled===!0&&ce.isPresenting===!0&&(ce.cameraAutoUpdate===!0&&ce.updateCamera(L),L=ce.getCamera()),v.isScene===!0&&v.onBeforeRender(y,v,L,D),p=Ne.get(v,M.length),p.init(L),M.push(p),se.multiplyMatrices(L.projectionMatrix,L.matrixWorldInverse),Qe.setFromProjectionMatrix(se,mn,L.reversedDepth),Y=this.localClippingEnabled,it=fe.init(this.clippingPlanes,Y),m=W.get(v,T.length),m.init(),T.push(m),ce.enabled===!0&&ce.isPresenting===!0){let le=y.xr.getDepthSensingMesh();le!==null&&Ho(le,L,-1/0,y.sortObjects)}Ho(v,L,0,y.sortObjects),m.finish(),y.sortObjects===!0&&m.sort(Q,he),et=ce.enabled===!1||ce.isPresenting===!1||ce.hasDepthSensing()===!1,et&&Re.addToRenderList(m,v),this.info.render.frame++,it===!0&&fe.beginShadows();let B=p.state.shadowsArray;Ce.render(B,v,L),it===!0&&fe.endShadows(),this.info.autoReset===!0&&this.info.reset();let z=m.opaque,F=m.transmissive;if(p.setupLights(),L.isArrayCamera){let le=L.cameras;if(F.length>0)for(let ye=0,Te=le.length;ye<Te;ye++){let be=le[ye];Fc(z,F,v,be)}et&&Re.render(v);for(let ye=0,Te=le.length;ye<Te;ye++){let be=le[ye];Uc(m,v,be,be.viewport)}}else F.length>0&&Fc(z,F,v,L),et&&Re.render(v),Uc(m,v,L);D!==null&&P===0&&(me.updateMultisampleRenderTarget(D),me.updateRenderTargetMipmap(D)),v.isScene===!0&&v.onAfterRender(y,v,L),ve.resetDefaultState(),b=-1,w=null,M.pop(),M.length>0?(p=M[M.length-1],it===!0&&fe.setGlobalState(y.clippingPlanes,p.state.camera)):p=null,T.pop(),T.length>0?m=T[T.length-1]:m=null};function Ho(v,L,B,z){if(v.visible===!1)return;if(v.layers.test(L.layers)){if(v.isGroup)B=v.renderOrder;else if(v.isLOD)v.autoUpdate===!0&&v.update(L);else if(v.isLight)p.pushLight(v),v.castShadow&&p.pushShadow(v);else if(v.isSprite){if(!v.frustumCulled||Qe.intersectsSprite(v)){z&&Ue.setFromMatrixPosition(v.matrixWorld).applyMatrix4(se);let ye=O.update(v),Te=v.material;Te.visible&&m.push(v,ye,Te,B,Ue.z,null)}}else if((v.isMesh||v.isLine||v.isPoints)&&(!v.frustumCulled||Qe.intersectsObject(v))){let ye=O.update(v),Te=v.material;if(z&&(v.boundingSphere!==void 0?(v.boundingSphere===null&&v.computeBoundingSphere(),Ue.copy(v.boundingSphere.center)):(ye.boundingSphere===null&&ye.computeBoundingSphere(),Ue.copy(ye.boundingSphere.center)),Ue.applyMatrix4(v.matrixWorld).applyMatrix4(se)),Array.isArray(Te)){let be=ye.groups;for(let ke=0,Ve=be.length;ke<Ve;ke++){let Fe=be[ke],tt=Te[Fe.materialIndex];tt&&tt.visible&&m.push(v,ye,tt,B,Ue.z,Fe)}}else Te.visible&&m.push(v,ye,Te,B,Ue.z,null)}}let le=v.children;for(let ye=0,Te=le.length;ye<Te;ye++)Ho(le[ye],L,B,z)}function Uc(v,L,B,z){let F=v.opaque,le=v.transmissive,ye=v.transparent;p.setupLightsView(B),it===!0&&fe.setGlobalState(y.clippingPlanes,B),z&&$.viewport(C.copy(z)),F.length>0&&Nr(F,L,B),le.length>0&&Nr(le,L,B),ye.length>0&&Nr(ye,L,B),$.buffers.depth.setTest(!0),$.buffers.depth.setMask(!0),$.buffers.color.setMask(!0),$.setPolygonOffset(!1)}function Fc(v,L,B,z){if((B.isScene===!0?B.overrideMaterial:null)!==null)return;p.state.transmissionRenderTarget[z.id]===void 0&&(p.state.transmissionRenderTarget[z.id]=new Sn(1,1,{generateMipmaps:!0,type:J.has("EXT_color_buffer_half_float")||J.has("EXT_color_buffer_float")?ys:vn,minFilter:pi,samples:4,stencilBuffer:r,resolveDepthBuffer:!1,resolveStencilBuffer:!1,colorSpace:st.workingColorSpace}));let le=p.state.transmissionRenderTarget[z.id],ye=z.viewport||C;le.setSize(ye.z*y.transmissionResolutionScale,ye.w*y.transmissionResolutionScale);let Te=y.getRenderTarget(),be=y.getActiveCubeFace(),ke=y.getActiveMipmapLevel();y.setRenderTarget(le),y.getClearColor(q),X=y.getClearAlpha(),X<1&&y.setClearColor(16777215,.5),y.clear(),et&&Re.render(B);let Ve=y.toneMapping;y.toneMapping=qn;let Fe=z.viewport;if(z.viewport!==void 0&&(z.viewport=void 0),p.setupLightsView(z),it===!0&&fe.setGlobalState(y.clippingPlanes,z),Nr(v,B,z),me.updateMultisampleRenderTarget(le),me.updateRenderTargetMipmap(le),J.has("WEBGL_multisampled_render_to_texture")===!1){let tt=!1;for(let lt=0,bt=L.length;lt<bt;lt++){let mt=L[lt],dt=mt.object,Oe=mt.geometry,xt=mt.material,rt=mt.group;if(xt.side===An&&dt.layers.test(z.layers)){let Zt=xt.side;xt.side=Wt,xt.needsUpdate=!0,Oc(dt,B,z,Oe,xt,rt),xt.side=Zt,xt.needsUpdate=!0,tt=!0}}tt===!0&&(me.updateMultisampleRenderTarget(le),me.updateRenderTargetMipmap(le))}y.setRenderTarget(Te,be,ke),y.setClearColor(q,X),Fe!==void 0&&(z.viewport=Fe),y.toneMapping=Ve}function Nr(v,L,B){let z=L.isScene===!0?L.overrideMaterial:null;for(let F=0,le=v.length;F<le;F++){let ye=v[F],Te=ye.object,be=ye.geometry,ke=ye.group,Ve=ye.material;Ve.allowOverride===!0&&z!==null&&(Ve=z),Te.layers.test(B.layers)&&Oc(Te,L,B,be,Ve,ke)}}function Oc(v,L,B,z,F,le){v.onBeforeRender(y,L,B,z,F,le),v.modelViewMatrix.multiplyMatrices(B.matrixWorldInverse,v.matrixWorld),v.normalMatrix.getNormalMatrix(v.modelViewMatrix),F.onBeforeRender(y,L,B,z,v,le),F.transparent===!0&&F.side===An&&F.forceSinglePass===!1?(F.side=Wt,F.needsUpdate=!0,y.renderBufferDirect(B,L,z,F,v,le),F.side=Wn,F.needsUpdate=!0,y.renderBufferDirect(B,L,z,F,v,le),F.side=An):y.renderBufferDirect(B,L,z,F,v,le),v.onAfterRender(y,L,B,z,F,le)}function Dr(v,L,B){L.isScene!==!0&&(L=Ae);let z=re.get(v),F=p.state.lights,le=p.state.shadowsArray,ye=F.state.version,Te=H.getParameters(v,F.state,le,L,B),be=H.getProgramCacheKey(Te),ke=z.programs;z.environment=v.isMeshStandardMaterial?L.environment:null,z.fog=L.fog,z.envMap=(v.isMeshStandardMaterial?He:We).get(v.envMap||z.environment),z.envMapRotation=z.environment!==null&&v.envMap===null?L.environmentRotation:v.envMapRotation,ke===void 0&&(v.addEventListener("dispose",K),ke=new Map,z.programs=ke);let Ve=ke.get(be);if(Ve!==void 0){if(z.currentProgram===Ve&&z.lightsStateVersion===ye)return Bc(v,Te),Ve}else Te.uniforms=H.getUniforms(v),v.onBeforeCompile(Te,y),Ve=H.acquireProgram(Te,be),ke.set(be,Ve),z.uniforms=Te.uniforms;let Fe=z.uniforms;return(!v.isShaderMaterial&&!v.isRawShaderMaterial||v.clipping===!0)&&(Fe.clippingPlanes=fe.uniform),Bc(v,Te),z.needsLights=Yd(v),z.lightsStateVersion=ye,z.needsLights&&(Fe.ambientLightColor.value=F.state.ambient,Fe.lightProbe.value=F.state.probe,Fe.directionalLights.value=F.state.directional,Fe.directionalLightShadows.value=F.state.directionalShadow,Fe.spotLights.value=F.state.spot,Fe.spotLightShadows.value=F.state.spotShadow,Fe.rectAreaLights.value=F.state.rectArea,Fe.ltc_1.value=F.state.rectAreaLTC1,Fe.ltc_2.value=F.state.rectAreaLTC2,Fe.pointLights.value=F.state.point,Fe.pointLightShadows.value=F.state.pointShadow,Fe.hemisphereLights.value=F.state.hemi,Fe.directionalShadowMap.value=F.state.directionalShadowMap,Fe.directionalShadowMatrix.value=F.state.directionalShadowMatrix,Fe.spotShadowMap.value=F.state.spotShadowMap,Fe.spotLightMatrix.value=F.state.spotLightMatrix,Fe.spotLightMap.value=F.state.spotLightMap,Fe.pointShadowMap.value=F.state.pointShadowMap,Fe.pointShadowMatrix.value=F.state.pointShadowMatrix),z.currentProgram=Ve,z.uniformsList=null,Ve}function kc(v){if(v.uniformsList===null){let L=v.currentProgram.getUniforms();v.uniformsList=Ts.seqWithValue(L.seq,v.uniforms)}return v.uniformsList}function Bc(v,L){let B=re.get(v);B.outputColorSpace=L.outputColorSpace,B.batching=L.batching,B.batchingColor=L.batchingColor,B.instancing=L.instancing,B.instancingColor=L.instancingColor,B.instancingMorph=L.instancingMorph,B.skinning=L.skinning,B.morphTargets=L.morphTargets,B.morphNormals=L.morphNormals,B.morphColors=L.morphColors,B.morphTargetsCount=L.morphTargetsCount,B.numClippingPlanes=L.numClippingPlanes,B.numIntersection=L.numClipIntersection,B.vertexAlphas=L.vertexAlphas,B.vertexTangents=L.vertexTangents,B.toneMapping=L.toneMapping}function Xd(v,L,B,z,F){L.isScene!==!0&&(L=Ae),me.resetTextureUnits();let le=L.fog,ye=z.isMeshStandardMaterial?L.environment:null,Te=D===null?y.outputColorSpace:D.isXRRenderTarget===!0?D.texture.colorSpace:Ri,be=(z.isMeshStandardMaterial?He:We).get(z.envMap||ye),ke=z.vertexColors===!0&&!!B.attributes.color&&B.attributes.color.itemSize===4,Ve=!!B.attributes.tangent&&(!!z.normalMap||z.anisotropy>0),Fe=!!B.morphAttributes.position,tt=!!B.morphAttributes.normal,lt=!!B.morphAttributes.color,bt=qn;z.toneMapped&&(D===null||D.isXRRenderTarget===!0)&&(bt=y.toneMapping);let mt=B.morphAttributes.position||B.morphAttributes.normal||B.morphAttributes.color,dt=mt!==void 0?mt.length:0,Oe=re.get(z),xt=p.state.lights;if(it===!0&&(Y===!0||v!==w)){let Bt=v===w&&z.id===b;fe.setState(z,v,Bt)}let rt=!1;z.version===Oe.__version?(Oe.needsLights&&Oe.lightsStateVersion!==xt.state.version||Oe.outputColorSpace!==Te||F.isBatchedMesh&&Oe.batching===!1||!F.isBatchedMesh&&Oe.batching===!0||F.isBatchedMesh&&Oe.batchingColor===!0&&F.colorTexture===null||F.isBatchedMesh&&Oe.batchingColor===!1&&F.colorTexture!==null||F.isInstancedMesh&&Oe.instancing===!1||!F.isInstancedMesh&&Oe.instancing===!0||F.isSkinnedMesh&&Oe.skinning===!1||!F.isSkinnedMesh&&Oe.skinning===!0||F.isInstancedMesh&&Oe.instancingColor===!0&&F.instanceColor===null||F.isInstancedMesh&&Oe.instancingColor===!1&&F.instanceColor!==null||F.isInstancedMesh&&Oe.instancingMorph===!0&&F.morphTexture===null||F.isInstancedMesh&&Oe.instancingMorph===!1&&F.morphTexture!==null||Oe.envMap!==be||z.fog===!0&&Oe.fog!==le||Oe.numClippingPlanes!==void 0&&(Oe.numClippingPlanes!==fe.numPlanes||Oe.numIntersection!==fe.numIntersection)||Oe.vertexAlphas!==ke||Oe.vertexTangents!==Ve||Oe.morphTargets!==Fe||Oe.morphNormals!==tt||Oe.morphColors!==lt||Oe.toneMapping!==bt||Oe.morphTargetsCount!==dt)&&(rt=!0):(rt=!0,Oe.__version=z.version);let Zt=Oe.currentProgram;rt===!0&&(Zt=Dr(z,L,F));let Gi=!1,Jt=!1,Cs=!1,vt=Zt.getUniforms(),nn=Oe.uniforms;if($.useProgram(Zt.program)&&(Gi=!0,Jt=!0,Cs=!0),z.id!==b&&(b=z.id,Jt=!0),Gi||w!==v){$.buffers.depth.getReversed()&&v.reversedDepth!==!0&&(v._reversedDepth=!0,v.updateProjectionMatrix()),vt.setValue(A,"projectionMatrix",v.projectionMatrix),vt.setValue(A,"viewMatrix",v.matrixWorldInverse);let Xt=vt.map.cameraPosition;Xt!==void 0&&Xt.setValue(A,Me.setFromMatrixPosition(v.matrixWorld)),Z.logarithmicDepthBuffer&&vt.setValue(A,"logDepthBufFC",2/(Math.log(v.far+1)/Math.LN2)),(z.isMeshPhongMaterial||z.isMeshToonMaterial||z.isMeshLambertMaterial||z.isMeshBasicMaterial||z.isMeshStandardMaterial||z.isShaderMaterial)&&vt.setValue(A,"isOrthographic",v.isOrthographicCamera===!0),w!==v&&(w=v,Jt=!0,Cs=!0)}if(F.isSkinnedMesh){vt.setOptional(A,F,"bindMatrix"),vt.setOptional(A,F,"bindMatrixInverse");let Bt=F.skeleton;Bt&&(Bt.boneTexture===null&&Bt.computeBoneTexture(),vt.setValue(A,"boneTexture",Bt.boneTexture,me))}F.isBatchedMesh&&(vt.setOptional(A,F,"batchingTexture"),vt.setValue(A,"batchingTexture",F._matricesTexture,me),vt.setOptional(A,F,"batchingIdTexture"),vt.setValue(A,"batchingIdTexture",F._indirectTexture,me),vt.setOptional(A,F,"batchingColorTexture"),F._colorsTexture!==null&&vt.setValue(A,"batchingColorTexture",F._colorsTexture,me));let sn=B.morphAttributes;if((sn.position!==void 0||sn.normal!==void 0||sn.color!==void 0)&&ae.update(F,B,Zt),(Jt||Oe.receiveShadow!==F.receiveShadow)&&(Oe.receiveShadow=F.receiveShadow,vt.setValue(A,"receiveShadow",F.receiveShadow)),z.isMeshGouraudMaterial&&z.envMap!==null&&(nn.envMap.value=be,nn.flipEnvMap.value=be.isCubeTexture&&be.isRenderTargetTexture===!1?-1:1),z.isMeshStandardMaterial&&z.envMap===null&&L.environment!==null&&(nn.envMapIntensity.value=L.environmentIntensity),Jt&&(vt.setValue(A,"toneMappingExposure",y.toneMappingExposure),Oe.needsLights&&qd(nn,Cs),le&&z.fog===!0&&ee.refreshFogUniforms(nn,le),ee.refreshMaterialUniforms(nn,z,U,te,p.state.transmissionRenderTarget[v.id]),Ts.upload(A,kc(Oe),nn,me)),z.isShaderMaterial&&z.uniformsNeedUpdate===!0&&(Ts.upload(A,kc(Oe),nn,me),z.uniformsNeedUpdate=!1),z.isSpriteMaterial&&vt.setValue(A,"center",F.center),vt.setValue(A,"modelViewMatrix",F.modelViewMatrix),vt.setValue(A,"normalMatrix",F.normalMatrix),vt.setValue(A,"modelMatrix",F.matrixWorld),z.isShaderMaterial||z.isRawShaderMaterial){let Bt=z.uniformsGroups;for(let Xt=0,Go=Bt.length;Xt<Go;Xt++){let vi=Bt[Xt];Ze.update(vi,Zt),Ze.bind(vi,Zt)}}return Zt}function qd(v,L){v.ambientLightColor.needsUpdate=L,v.lightProbe.needsUpdate=L,v.directionalLights.needsUpdate=L,v.directionalLightShadows.needsUpdate=L,v.pointLights.needsUpdate=L,v.pointLightShadows.needsUpdate=L,v.spotLights.needsUpdate=L,v.spotLightShadows.needsUpdate=L,v.rectAreaLights.needsUpdate=L,v.hemisphereLights.needsUpdate=L}function Yd(v){return v.isMeshLambertMaterial||v.isMeshToonMaterial||v.isMeshPhongMaterial||v.isMeshStandardMaterial||v.isShadowMaterial||v.isShaderMaterial&&v.lights===!0}this.getActiveCubeFace=function(){return E},this.getActiveMipmapLevel=function(){return P},this.getRenderTarget=function(){return D},this.setRenderTargetTextures=function(v,L,B){let z=re.get(v);z.__autoAllocateDepthBuffer=v.resolveDepthBuffer===!1,z.__autoAllocateDepthBuffer===!1&&(z.__useRenderToTexture=!1),re.get(v.texture).__webglTexture=L,re.get(v.depthTexture).__webglTexture=z.__autoAllocateDepthBuffer?void 0:B,z.__hasExternalTextures=!0},this.setRenderTargetFramebuffer=function(v,L){let B=re.get(v);B.__webglFramebuffer=L,B.__useDefaultFramebuffer=L===void 0};let $d=A.createFramebuffer();this.setRenderTarget=function(v,L=0,B=0){D=v,E=L,P=B;let z=!0,F=null,le=!1,ye=!1;if(v){let be=re.get(v);if(be.__useDefaultFramebuffer!==void 0)$.bindFramebuffer(A.FRAMEBUFFER,null),z=!1;else if(be.__webglFramebuffer===void 0)me.setupRenderTarget(v);else if(be.__hasExternalTextures)me.rebindTextures(v,re.get(v.texture).__webglTexture,re.get(v.depthTexture).__webglTexture);else if(v.depthBuffer){let Fe=v.depthTexture;if(be.__boundDepthTexture!==Fe){if(Fe!==null&&re.has(Fe)&&(v.width!==Fe.image.width||v.height!==Fe.image.height))throw new Error("WebGLRenderTarget: Attached DepthTexture is initialized to the incorrect size.");me.setupDepthRenderbuffer(v)}}let ke=v.texture;(ke.isData3DTexture||ke.isDataArrayTexture||ke.isCompressedArrayTexture)&&(ye=!0);let Ve=re.get(v).__webglFramebuffer;v.isWebGLCubeRenderTarget?(Array.isArray(Ve[L])?F=Ve[L][B]:F=Ve[L],le=!0):v.samples>0&&me.useMultisampledRTT(v)===!1?F=re.get(v).__webglMultisampledFramebuffer:Array.isArray(Ve)?F=Ve[B]:F=Ve,C.copy(v.viewport),k.copy(v.scissor),G=v.scissorTest}else C.copy(ue).multiplyScalar(U).floor(),k.copy(ze).multiplyScalar(U).floor(),G=je;if(B!==0&&(F=$d),$.bindFramebuffer(A.FRAMEBUFFER,F)&&z&&$.drawBuffers(v,F),$.viewport(C),$.scissor(k),$.setScissorTest(G),le){let be=re.get(v.texture);A.framebufferTexture2D(A.FRAMEBUFFER,A.COLOR_ATTACHMENT0,A.TEXTURE_CUBE_MAP_POSITIVE_X+L,be.__webglTexture,B)}else if(ye){let be=L;for(let ke=0;ke<v.textures.length;ke++){let Ve=re.get(v.textures[ke]);A.framebufferTextureLayer(A.FRAMEBUFFER,A.COLOR_ATTACHMENT0+ke,Ve.__webglTexture,B,be)}}else if(v!==null&&B!==0){let be=re.get(v.texture);A.framebufferTexture2D(A.FRAMEBUFFER,A.COLOR_ATTACHMENT0,A.TEXTURE_2D,be.__webglTexture,B)}b=-1},this.readRenderTargetPixels=function(v,L,B,z,F,le,ye,Te=0){if(!(v&&v.isWebGLRenderTarget)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");return}let be=re.get(v).__webglFramebuffer;if(v.isWebGLCubeRenderTarget&&ye!==void 0&&(be=be[ye]),be){$.bindFramebuffer(A.FRAMEBUFFER,be);try{let ke=v.textures[Te],Ve=ke.format,Fe=ke.type;if(!Z.textureFormatReadable(Ve)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in RGBA or implementation defined format.");return}if(!Z.textureTypeReadable(Fe)){console.error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not in UnsignedByteType or implementation defined type.");return}L>=0&&L<=v.width-z&&B>=0&&B<=v.height-F&&(v.textures.length>1&&A.readBuffer(A.COLOR_ATTACHMENT0+Te),A.readPixels(L,B,z,F,Le.convert(Ve),Le.convert(Fe),le))}finally{let ke=D!==null?re.get(D).__webglFramebuffer:null;$.bindFramebuffer(A.FRAMEBUFFER,ke)}}},this.readRenderTargetPixelsAsync=async function(v,L,B,z,F,le,ye,Te=0){if(!(v&&v.isWebGLRenderTarget))throw new Error("THREE.WebGLRenderer.readRenderTargetPixels: renderTarget is not THREE.WebGLRenderTarget.");let be=re.get(v).__webglFramebuffer;if(v.isWebGLCubeRenderTarget&&ye!==void 0&&(be=be[ye]),be)if(L>=0&&L<=v.width-z&&B>=0&&B<=v.height-F){$.bindFramebuffer(A.FRAMEBUFFER,be);let ke=v.textures[Te],Ve=ke.format,Fe=ke.type;if(!Z.textureFormatReadable(Ve))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in RGBA or implementation defined format.");if(!Z.textureTypeReadable(Fe))throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: renderTarget is not in UnsignedByteType or implementation defined type.");let tt=A.createBuffer();A.bindBuffer(A.PIXEL_PACK_BUFFER,tt),A.bufferData(A.PIXEL_PACK_BUFFER,le.byteLength,A.STREAM_READ),v.textures.length>1&&A.readBuffer(A.COLOR_ATTACHMENT0+Te),A.readPixels(L,B,z,F,Le.convert(Ve),Le.convert(Fe),0);let lt=D!==null?re.get(D).__webglFramebuffer:null;$.bindFramebuffer(A.FRAMEBUFFER,lt);let bt=A.fenceSync(A.SYNC_GPU_COMMANDS_COMPLETE,0);return A.flush(),await Lu(A,bt,4),A.bindBuffer(A.PIXEL_PACK_BUFFER,tt),A.getBufferSubData(A.PIXEL_PACK_BUFFER,0,le),A.deleteBuffer(tt),A.deleteSync(bt),le}else throw new Error("THREE.WebGLRenderer.readRenderTargetPixelsAsync: requested read bounds are out of range.")},this.copyFramebufferToTexture=function(v,L=null,B=0){let z=Math.pow(2,-B),F=Math.floor(v.image.width*z),le=Math.floor(v.image.height*z),ye=L!==null?L.x:0,Te=L!==null?L.y:0;me.setTexture2D(v,0),A.copyTexSubImage2D(A.TEXTURE_2D,B,0,0,ye,Te,F,le),$.unbindTexture()};let Zd=A.createFramebuffer(),Jd=A.createFramebuffer();this.copyTextureToTexture=function(v,L,B=null,z=null,F=0,le=null){le===null&&(F!==0?(hs("WebGLRenderer: copyTextureToTexture function signature has changed to support src and dst mipmap levels."),le=F,F=0):le=0);let ye,Te,be,ke,Ve,Fe,tt,lt,bt,mt=v.isCompressedTexture?v.mipmaps[le]:v.image;if(B!==null)ye=B.max.x-B.min.x,Te=B.max.y-B.min.y,be=B.isBox3?B.max.z-B.min.z:1,ke=B.min.x,Ve=B.min.y,Fe=B.isBox3?B.min.z:0;else{let sn=Math.pow(2,-F);ye=Math.floor(mt.width*sn),Te=Math.floor(mt.height*sn),v.isDataArrayTexture?be=mt.depth:v.isData3DTexture?be=Math.floor(mt.depth*sn):be=1,ke=0,Ve=0,Fe=0}z!==null?(tt=z.x,lt=z.y,bt=z.z):(tt=0,lt=0,bt=0);let dt=Le.convert(L.format),Oe=Le.convert(L.type),xt;L.isData3DTexture?(me.setTexture3D(L,0),xt=A.TEXTURE_3D):L.isDataArrayTexture||L.isCompressedArrayTexture?(me.setTexture2DArray(L,0),xt=A.TEXTURE_2D_ARRAY):(me.setTexture2D(L,0),xt=A.TEXTURE_2D),A.pixelStorei(A.UNPACK_FLIP_Y_WEBGL,L.flipY),A.pixelStorei(A.UNPACK_PREMULTIPLY_ALPHA_WEBGL,L.premultiplyAlpha),A.pixelStorei(A.UNPACK_ALIGNMENT,L.unpackAlignment);let rt=A.getParameter(A.UNPACK_ROW_LENGTH),Zt=A.getParameter(A.UNPACK_IMAGE_HEIGHT),Gi=A.getParameter(A.UNPACK_SKIP_PIXELS),Jt=A.getParameter(A.UNPACK_SKIP_ROWS),Cs=A.getParameter(A.UNPACK_SKIP_IMAGES);A.pixelStorei(A.UNPACK_ROW_LENGTH,mt.width),A.pixelStorei(A.UNPACK_IMAGE_HEIGHT,mt.height),A.pixelStorei(A.UNPACK_SKIP_PIXELS,ke),A.pixelStorei(A.UNPACK_SKIP_ROWS,Ve),A.pixelStorei(A.UNPACK_SKIP_IMAGES,Fe);let vt=v.isDataArrayTexture||v.isData3DTexture,nn=L.isDataArrayTexture||L.isData3DTexture;if(v.isDepthTexture){let sn=re.get(v),Bt=re.get(L),Xt=re.get(sn.__renderTarget),Go=re.get(Bt.__renderTarget);$.bindFramebuffer(A.READ_FRAMEBUFFER,Xt.__webglFramebuffer),$.bindFramebuffer(A.DRAW_FRAMEBUFFER,Go.__webglFramebuffer);for(let vi=0;vi<be;vi++)vt&&(A.framebufferTextureLayer(A.READ_FRAMEBUFFER,A.COLOR_ATTACHMENT0,re.get(v).__webglTexture,F,Fe+vi),A.framebufferTextureLayer(A.DRAW_FRAMEBUFFER,A.COLOR_ATTACHMENT0,re.get(L).__webglTexture,le,bt+vi)),A.blitFramebuffer(ke,Ve,ye,Te,tt,lt,ye,Te,A.DEPTH_BUFFER_BIT,A.NEAREST);$.bindFramebuffer(A.READ_FRAMEBUFFER,null),$.bindFramebuffer(A.DRAW_FRAMEBUFFER,null)}else if(F!==0||v.isRenderTargetTexture||re.has(v)){let sn=re.get(v),Bt=re.get(L);$.bindFramebuffer(A.READ_FRAMEBUFFER,Zd),$.bindFramebuffer(A.DRAW_FRAMEBUFFER,Jd);for(let Xt=0;Xt<be;Xt++)vt?A.framebufferTextureLayer(A.READ_FRAMEBUFFER,A.COLOR_ATTACHMENT0,sn.__webglTexture,F,Fe+Xt):A.framebufferTexture2D(A.READ_FRAMEBUFFER,A.COLOR_ATTACHMENT0,A.TEXTURE_2D,sn.__webglTexture,F),nn?A.framebufferTextureLayer(A.DRAW_FRAMEBUFFER,A.COLOR_ATTACHMENT0,Bt.__webglTexture,le,bt+Xt):A.framebufferTexture2D(A.DRAW_FRAMEBUFFER,A.COLOR_ATTACHMENT0,A.TEXTURE_2D,Bt.__webglTexture,le),F!==0?A.blitFramebuffer(ke,Ve,ye,Te,tt,lt,ye,Te,A.COLOR_BUFFER_BIT,A.NEAREST):nn?A.copyTexSubImage3D(xt,le,tt,lt,bt+Xt,ke,Ve,ye,Te):A.copyTexSubImage2D(xt,le,tt,lt,ke,Ve,ye,Te);$.bindFramebuffer(A.READ_FRAMEBUFFER,null),$.bindFramebuffer(A.DRAW_FRAMEBUFFER,null)}else nn?v.isDataTexture||v.isData3DTexture?A.texSubImage3D(xt,le,tt,lt,bt,ye,Te,be,dt,Oe,mt.data):L.isCompressedArrayTexture?A.compressedTexSubImage3D(xt,le,tt,lt,bt,ye,Te,be,dt,mt.data):A.texSubImage3D(xt,le,tt,lt,bt,ye,Te,be,dt,Oe,mt):v.isDataTexture?A.texSubImage2D(A.TEXTURE_2D,le,tt,lt,ye,Te,dt,Oe,mt.data):v.isCompressedTexture?A.compressedTexSubImage2D(A.TEXTURE_2D,le,tt,lt,mt.width,mt.height,dt,mt.data):A.texSubImage2D(A.TEXTURE_2D,le,tt,lt,ye,Te,dt,Oe,mt);A.pixelStorei(A.UNPACK_ROW_LENGTH,rt),A.pixelStorei(A.UNPACK_IMAGE_HEIGHT,Zt),A.pixelStorei(A.UNPACK_SKIP_PIXELS,Gi),A.pixelStorei(A.UNPACK_SKIP_ROWS,Jt),A.pixelStorei(A.UNPACK_SKIP_IMAGES,Cs),le===0&&L.generateMipmaps&&A.generateMipmap(xt),$.unbindTexture()},this.initRenderTarget=function(v){re.get(v).__webglFramebuffer===void 0&&me.setupRenderTarget(v)},this.initTexture=function(v){v.isCubeTexture?me.setTextureCube(v,0):v.isData3DTexture?me.setTexture3D(v,0):v.isDataArrayTexture||v.isCompressedArrayTexture?me.setTexture2DArray(v,0):me.setTexture2D(v,0),$.unbindTexture()},this.resetState=function(){E=0,P=0,D=null,$.reset(),ve.reset()},typeof __THREE_DEVTOOLS__<"u"&&__THREE_DEVTOOLS__.dispatchEvent(new CustomEvent("observe",{detail:this}))}get coordinateSystem(){return mn}get outputColorSpace(){return this._outputColorSpace}set outputColorSpace(e){this._outputColorSpace=e;let t=this.getContext();t.drawingBufferColorSpace=st._getDrawingBufferColorSpace(e),t.unpackColorSpace=st._getUnpackColorSpace()}};var gd={type:"change"},Ec={type:"start"},xd={type:"end"},Fo=new fs,_d=new an,y0=Math.cos(70*ic.DEG2RAD),Ct=new N,$t=2*Math.PI,ht={NONE:-1,ROTATE:0,DOLLY:1,PAN:2,TOUCH_ROTATE:3,TOUCH_PAN:4,TOUCH_DOLLY_PAN:5,TOUCH_DOLLY_ROTATE:6},Tc=1e-6,Oo=class extends br{constructor(e,t=null){super(e,t),this.state=ht.NONE,this.target=new N,this.cursor=new N,this.minDistance=0,this.maxDistance=1/0,this.minZoom=0,this.maxZoom=1/0,this.minTargetRadius=0,this.maxTargetRadius=1/0,this.minPolarAngle=0,this.maxPolarAngle=Math.PI,this.minAzimuthAngle=-1/0,this.maxAzimuthAngle=1/0,this.enableDamping=!1,this.dampingFactor=.05,this.enableZoom=!0,this.zoomSpeed=1,this.enableRotate=!0,this.rotateSpeed=1,this.keyRotateSpeed=1,this.enablePan=!0,this.panSpeed=1,this.screenSpacePanning=!0,this.keyPanSpeed=7,this.zoomToCursor=!1,this.autoRotate=!1,this.autoRotateSpeed=2,this.keys={LEFT:"ArrowLeft",UP:"ArrowUp",RIGHT:"ArrowRight",BOTTOM:"ArrowDown"},this.mouseButtons={LEFT:di.ROTATE,MIDDLE:di.DOLLY,RIGHT:di.PAN},this.touches={ONE:fi.ROTATE,TWO:fi.DOLLY_PAN},this.target0=this.target.clone(),this.position0=this.object.position.clone(),this.zoom0=this.object.zoom,this._domElementKeyEvents=null,this._lastPosition=new N,this._lastQuaternion=new ln,this._lastTargetPosition=new N,this._quat=new ln().setFromUnitVectors(e.up,new N(0,1,0)),this._quatInverse=this._quat.clone().invert(),this._spherical=new ui,this._sphericalDelta=new ui,this._scale=1,this._panOffset=new N,this._rotateStart=new de,this._rotateEnd=new de,this._rotateDelta=new de,this._panStart=new de,this._panEnd=new de,this._panDelta=new de,this._dollyStart=new de,this._dollyEnd=new de,this._dollyDelta=new de,this._dollyDirection=new N,this._mouse=new de,this._performCursorZoom=!1,this._pointers=[],this._pointerPositions={},this._controlActive=!1,this._onPointerMove=b0.bind(this),this._onPointerDown=w0.bind(this),this._onPointerUp=M0.bind(this),this._onContextMenu=P0.bind(this),this._onMouseWheel=E0.bind(this),this._onKeyDown=A0.bind(this),this._onTouchStart=C0.bind(this),this._onTouchMove=R0.bind(this),this._onMouseDown=S0.bind(this),this._onMouseMove=T0.bind(this),this._interceptControlDown=I0.bind(this),this._interceptControlUp=N0.bind(this),this.domElement!==null&&this.connect(this.domElement),this.update()}connect(e){super.connect(e),this.domElement.addEventListener("pointerdown",this._onPointerDown),this.domElement.addEventListener("pointercancel",this._onPointerUp),this.domElement.addEventListener("contextmenu",this._onContextMenu),this.domElement.addEventListener("wheel",this._onMouseWheel,{passive:!1}),this.domElement.getRootNode().addEventListener("keydown",this._interceptControlDown,{passive:!0,capture:!0}),this.domElement.style.touchAction="none"}disconnect(){this.domElement.removeEventListener("pointerdown",this._onPointerDown),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.domElement.removeEventListener("pointercancel",this._onPointerUp),this.domElement.removeEventListener("wheel",this._onMouseWheel),this.domElement.removeEventListener("contextmenu",this._onContextMenu),this.stopListenToKeyEvents(),this.domElement.getRootNode().removeEventListener("keydown",this._interceptControlDown,{capture:!0}),this.domElement.style.touchAction="auto"}dispose(){this.disconnect()}getPolarAngle(){return this._spherical.phi}getAzimuthalAngle(){return this._spherical.theta}getDistance(){return this.object.position.distanceTo(this.target)}listenToKeyEvents(e){e.addEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=e}stopListenToKeyEvents(){this._domElementKeyEvents!==null&&(this._domElementKeyEvents.removeEventListener("keydown",this._onKeyDown),this._domElementKeyEvents=null)}saveState(){this.target0.copy(this.target),this.position0.copy(this.object.position),this.zoom0=this.object.zoom}reset(){this.target.copy(this.target0),this.object.position.copy(this.position0),this.object.zoom=this.zoom0,this.object.updateProjectionMatrix(),this.dispatchEvent(gd),this.update(),this.state=ht.NONE}update(e=null){let t=this.object.position;Ct.copy(t).sub(this.target),Ct.applyQuaternion(this._quat),this._spherical.setFromVector3(Ct),this.autoRotate&&this.state===ht.NONE&&this._rotateLeft(this._getAutoRotationAngle(e)),this.enableDamping?(this._spherical.theta+=this._sphericalDelta.theta*this.dampingFactor,this._spherical.phi+=this._sphericalDelta.phi*this.dampingFactor):(this._spherical.theta+=this._sphericalDelta.theta,this._spherical.phi+=this._sphericalDelta.phi);let i=this.minAzimuthAngle,s=this.maxAzimuthAngle;isFinite(i)&&isFinite(s)&&(i<-Math.PI?i+=$t:i>Math.PI&&(i-=$t),s<-Math.PI?s+=$t:s>Math.PI&&(s-=$t),i<=s?this._spherical.theta=Math.max(i,Math.min(s,this._spherical.theta)):this._spherical.theta=this._spherical.theta>(i+s)/2?Math.max(i,this._spherical.theta):Math.min(s,this._spherical.theta)),this._spherical.phi=Math.max(this.minPolarAngle,Math.min(this.maxPolarAngle,this._spherical.phi)),this._spherical.makeSafe(),this.enableDamping===!0?this.target.addScaledVector(this._panOffset,this.dampingFactor):this.target.add(this._panOffset),this.target.sub(this.cursor),this.target.clampLength(this.minTargetRadius,this.maxTargetRadius),this.target.add(this.cursor);let r=!1;if(this.zoomToCursor&&this._performCursorZoom||this.object.isOrthographicCamera)this._spherical.radius=this._clampDistance(this._spherical.radius);else{let a=this._spherical.radius;this._spherical.radius=this._clampDistance(this._spherical.radius*this._scale),r=a!=this._spherical.radius}if(Ct.setFromSpherical(this._spherical),Ct.applyQuaternion(this._quatInverse),t.copy(this.target).add(Ct),this.object.lookAt(this.target),this.enableDamping===!0?(this._sphericalDelta.theta*=1-this.dampingFactor,this._sphericalDelta.phi*=1-this.dampingFactor,this._panOffset.multiplyScalar(1-this.dampingFactor)):(this._sphericalDelta.set(0,0,0),this._panOffset.set(0,0,0)),this.zoomToCursor&&this._performCursorZoom){let a=null;if(this.object.isPerspectiveCamera){let o=Ct.length();a=this._clampDistance(o*this._scale);let c=o-a;this.object.position.addScaledVector(this._dollyDirection,c),this.object.updateMatrixWorld(),r=!!c}else if(this.object.isOrthographicCamera){let o=new N(this._mouse.x,this._mouse.y,0);o.unproject(this.object);let c=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),this.object.updateProjectionMatrix(),r=c!==this.object.zoom;let l=new N(this._mouse.x,this._mouse.y,0);l.unproject(this.object),this.object.position.sub(l).add(o),this.object.updateMatrixWorld(),a=Ct.length()}else console.warn("WARNING: OrbitControls.js encountered an unknown camera type - zoom to cursor disabled."),this.zoomToCursor=!1;a!==null&&(this.screenSpacePanning?this.target.set(0,0,-1).transformDirection(this.object.matrix).multiplyScalar(a).add(this.object.position):(Fo.origin.copy(this.object.position),Fo.direction.set(0,0,-1).transformDirection(this.object.matrix),Math.abs(this.object.up.dot(Fo.direction))<y0?this.object.lookAt(this.target):(_d.setFromNormalAndCoplanarPoint(this.object.up,this.target),Fo.intersectPlane(_d,this.target))))}else if(this.object.isOrthographicCamera){let a=this.object.zoom;this.object.zoom=Math.max(this.minZoom,Math.min(this.maxZoom,this.object.zoom/this._scale)),a!==this.object.zoom&&(this.object.updateProjectionMatrix(),r=!0)}return this._scale=1,this._performCursorZoom=!1,r||this._lastPosition.distanceToSquared(this.object.position)>Tc||8*(1-this._lastQuaternion.dot(this.object.quaternion))>Tc||this._lastTargetPosition.distanceToSquared(this.target)>Tc?(this.dispatchEvent(gd),this._lastPosition.copy(this.object.position),this._lastQuaternion.copy(this.object.quaternion),this._lastTargetPosition.copy(this.target),!0):!1}_getAutoRotationAngle(e){return e!==null?$t/60*this.autoRotateSpeed*e:$t/60/60*this.autoRotateSpeed}_getZoomScale(e){let t=Math.abs(e*.01);return Math.pow(.95,this.zoomSpeed*t)}_rotateLeft(e){this._sphericalDelta.theta-=e}_rotateUp(e){this._sphericalDelta.phi-=e}_panLeft(e,t){Ct.setFromMatrixColumn(t,0),Ct.multiplyScalar(-e),this._panOffset.add(Ct)}_panUp(e,t){this.screenSpacePanning===!0?Ct.setFromMatrixColumn(t,1):(Ct.setFromMatrixColumn(t,0),Ct.crossVectors(this.object.up,Ct)),Ct.multiplyScalar(e),this._panOffset.add(Ct)}_pan(e,t){let i=this.domElement;if(this.object.isPerspectiveCamera){let s=this.object.position;Ct.copy(s).sub(this.target);let r=Ct.length();r*=Math.tan(this.object.fov/2*Math.PI/180),this._panLeft(2*e*r/i.clientHeight,this.object.matrix),this._panUp(2*t*r/i.clientHeight,this.object.matrix)}else this.object.isOrthographicCamera?(this._panLeft(e*(this.object.right-this.object.left)/this.object.zoom/i.clientWidth,this.object.matrix),this._panUp(t*(this.object.top-this.object.bottom)/this.object.zoom/i.clientHeight,this.object.matrix)):(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - pan disabled."),this.enablePan=!1)}_dollyOut(e){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale/=e:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_dollyIn(e){this.object.isPerspectiveCamera||this.object.isOrthographicCamera?this._scale*=e:(console.warn("WARNING: OrbitControls.js encountered an unknown camera type - dolly/zoom disabled."),this.enableZoom=!1)}_updateZoomParameters(e,t){if(!this.zoomToCursor)return;this._performCursorZoom=!0;let i=this.domElement.getBoundingClientRect(),s=e-i.left,r=t-i.top,a=i.width,o=i.height;this._mouse.x=s/a*2-1,this._mouse.y=-(r/o)*2+1,this._dollyDirection.set(this._mouse.x,this._mouse.y,1).unproject(this.object).sub(this.object.position).normalize()}_clampDistance(e){return Math.max(this.minDistance,Math.min(this.maxDistance,e))}_handleMouseDownRotate(e){this._rotateStart.set(e.clientX,e.clientY)}_handleMouseDownDolly(e){this._updateZoomParameters(e.clientX,e.clientX),this._dollyStart.set(e.clientX,e.clientY)}_handleMouseDownPan(e){this._panStart.set(e.clientX,e.clientY)}_handleMouseMoveRotate(e){this._rotateEnd.set(e.clientX,e.clientY),this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);let t=this.domElement;this._rotateLeft($t*this._rotateDelta.x/t.clientHeight),this._rotateUp($t*this._rotateDelta.y/t.clientHeight),this._rotateStart.copy(this._rotateEnd),this.update()}_handleMouseMoveDolly(e){this._dollyEnd.set(e.clientX,e.clientY),this._dollyDelta.subVectors(this._dollyEnd,this._dollyStart),this._dollyDelta.y>0?this._dollyOut(this._getZoomScale(this._dollyDelta.y)):this._dollyDelta.y<0&&this._dollyIn(this._getZoomScale(this._dollyDelta.y)),this._dollyStart.copy(this._dollyEnd),this.update()}_handleMouseMovePan(e){this._panEnd.set(e.clientX,e.clientY),this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd),this.update()}_handleMouseWheel(e){this._updateZoomParameters(e.clientX,e.clientY),e.deltaY<0?this._dollyIn(this._getZoomScale(e.deltaY)):e.deltaY>0&&this._dollyOut(this._getZoomScale(e.deltaY)),this.update()}_handleKeyDown(e){let t=!1;switch(e.code){case this.keys.UP:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateUp($t*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(0,this.keyPanSpeed),t=!0;break;case this.keys.BOTTOM:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateUp(-$t*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(0,-this.keyPanSpeed),t=!0;break;case this.keys.LEFT:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateLeft($t*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(this.keyPanSpeed,0),t=!0;break;case this.keys.RIGHT:e.ctrlKey||e.metaKey||e.shiftKey?this.enableRotate&&this._rotateLeft(-$t*this.keyRotateSpeed/this.domElement.clientHeight):this.enablePan&&this._pan(-this.keyPanSpeed,0),t=!0;break}t&&(e.preventDefault(),this.update())}_handleTouchStartRotate(e){if(this._pointers.length===1)this._rotateStart.set(e.pageX,e.pageY);else{let t=this._getSecondPointerPosition(e),i=.5*(e.pageX+t.x),s=.5*(e.pageY+t.y);this._rotateStart.set(i,s)}}_handleTouchStartPan(e){if(this._pointers.length===1)this._panStart.set(e.pageX,e.pageY);else{let t=this._getSecondPointerPosition(e),i=.5*(e.pageX+t.x),s=.5*(e.pageY+t.y);this._panStart.set(i,s)}}_handleTouchStartDolly(e){let t=this._getSecondPointerPosition(e),i=e.pageX-t.x,s=e.pageY-t.y,r=Math.sqrt(i*i+s*s);this._dollyStart.set(0,r)}_handleTouchStartDollyPan(e){this.enableZoom&&this._handleTouchStartDolly(e),this.enablePan&&this._handleTouchStartPan(e)}_handleTouchStartDollyRotate(e){this.enableZoom&&this._handleTouchStartDolly(e),this.enableRotate&&this._handleTouchStartRotate(e)}_handleTouchMoveRotate(e){if(this._pointers.length==1)this._rotateEnd.set(e.pageX,e.pageY);else{let i=this._getSecondPointerPosition(e),s=.5*(e.pageX+i.x),r=.5*(e.pageY+i.y);this._rotateEnd.set(s,r)}this._rotateDelta.subVectors(this._rotateEnd,this._rotateStart).multiplyScalar(this.rotateSpeed);let t=this.domElement;this._rotateLeft($t*this._rotateDelta.x/t.clientHeight),this._rotateUp($t*this._rotateDelta.y/t.clientHeight),this._rotateStart.copy(this._rotateEnd)}_handleTouchMovePan(e){if(this._pointers.length===1)this._panEnd.set(e.pageX,e.pageY);else{let t=this._getSecondPointerPosition(e),i=.5*(e.pageX+t.x),s=.5*(e.pageY+t.y);this._panEnd.set(i,s)}this._panDelta.subVectors(this._panEnd,this._panStart).multiplyScalar(this.panSpeed),this._pan(this._panDelta.x,this._panDelta.y),this._panStart.copy(this._panEnd)}_handleTouchMoveDolly(e){let t=this._getSecondPointerPosition(e),i=e.pageX-t.x,s=e.pageY-t.y,r=Math.sqrt(i*i+s*s);this._dollyEnd.set(0,r),this._dollyDelta.set(0,Math.pow(this._dollyEnd.y/this._dollyStart.y,this.zoomSpeed)),this._dollyOut(this._dollyDelta.y),this._dollyStart.copy(this._dollyEnd);let a=(e.pageX+t.x)*.5,o=(e.pageY+t.y)*.5;this._updateZoomParameters(a,o)}_handleTouchMoveDollyPan(e){this.enableZoom&&this._handleTouchMoveDolly(e),this.enablePan&&this._handleTouchMovePan(e)}_handleTouchMoveDollyRotate(e){this.enableZoom&&this._handleTouchMoveDolly(e),this.enableRotate&&this._handleTouchMoveRotate(e)}_addPointer(e){this._pointers.push(e.pointerId)}_removePointer(e){delete this._pointerPositions[e.pointerId];for(let t=0;t<this._pointers.length;t++)if(this._pointers[t]==e.pointerId){this._pointers.splice(t,1);return}}_isTrackingPointer(e){for(let t=0;t<this._pointers.length;t++)if(this._pointers[t]==e.pointerId)return!0;return!1}_trackPointer(e){let t=this._pointerPositions[e.pointerId];t===void 0&&(t=new de,this._pointerPositions[e.pointerId]=t),t.set(e.pageX,e.pageY)}_getSecondPointerPosition(e){let t=e.pointerId===this._pointers[0]?this._pointers[1]:this._pointers[0];return this._pointerPositions[t]}_customWheelEvent(e){let t=e.deltaMode,i={clientX:e.clientX,clientY:e.clientY,deltaY:e.deltaY};switch(t){case 1:i.deltaY*=16;break;case 2:i.deltaY*=100;break}return e.ctrlKey&&!this._controlActive&&(i.deltaY*=10),i}};function w0(n){this.enabled!==!1&&(this._pointers.length===0&&(this.domElement.setPointerCapture(n.pointerId),this.domElement.addEventListener("pointermove",this._onPointerMove),this.domElement.addEventListener("pointerup",this._onPointerUp)),!this._isTrackingPointer(n)&&(this._addPointer(n),n.pointerType==="touch"?this._onTouchStart(n):this._onMouseDown(n)))}function b0(n){this.enabled!==!1&&(n.pointerType==="touch"?this._onTouchMove(n):this._onMouseMove(n))}function M0(n){switch(this._removePointer(n),this._pointers.length){case 0:this.domElement.releasePointerCapture(n.pointerId),this.domElement.removeEventListener("pointermove",this._onPointerMove),this.domElement.removeEventListener("pointerup",this._onPointerUp),this.dispatchEvent(xd),this.state=ht.NONE;break;case 1:let e=this._pointers[0],t=this._pointerPositions[e];this._onTouchStart({pointerId:e,pageX:t.x,pageY:t.y});break}}function S0(n){let e;switch(n.button){case 0:e=this.mouseButtons.LEFT;break;case 1:e=this.mouseButtons.MIDDLE;break;case 2:e=this.mouseButtons.RIGHT;break;default:e=-1}switch(e){case di.DOLLY:if(this.enableZoom===!1)return;this._handleMouseDownDolly(n),this.state=ht.DOLLY;break;case di.ROTATE:if(n.ctrlKey||n.metaKey||n.shiftKey){if(this.enablePan===!1)return;this._handleMouseDownPan(n),this.state=ht.PAN}else{if(this.enableRotate===!1)return;this._handleMouseDownRotate(n),this.state=ht.ROTATE}break;case di.PAN:if(n.ctrlKey||n.metaKey||n.shiftKey){if(this.enableRotate===!1)return;this._handleMouseDownRotate(n),this.state=ht.ROTATE}else{if(this.enablePan===!1)return;this._handleMouseDownPan(n),this.state=ht.PAN}break;default:this.state=ht.NONE}this.state!==ht.NONE&&this.dispatchEvent(Ec)}function T0(n){switch(this.state){case ht.ROTATE:if(this.enableRotate===!1)return;this._handleMouseMoveRotate(n);break;case ht.DOLLY:if(this.enableZoom===!1)return;this._handleMouseMoveDolly(n);break;case ht.PAN:if(this.enablePan===!1)return;this._handleMouseMovePan(n);break}}function E0(n){this.enabled===!1||this.enableZoom===!1||this.state!==ht.NONE||(n.preventDefault(),this.dispatchEvent(Ec),this._handleMouseWheel(this._customWheelEvent(n)),this.dispatchEvent(xd))}function A0(n){this.enabled!==!1&&this._handleKeyDown(n)}function C0(n){switch(this._trackPointer(n),this._pointers.length){case 1:switch(this.touches.ONE){case fi.ROTATE:if(this.enableRotate===!1)return;this._handleTouchStartRotate(n),this.state=ht.TOUCH_ROTATE;break;case fi.PAN:if(this.enablePan===!1)return;this._handleTouchStartPan(n),this.state=ht.TOUCH_PAN;break;default:this.state=ht.NONE}break;case 2:switch(this.touches.TWO){case fi.DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchStartDollyPan(n),this.state=ht.TOUCH_DOLLY_PAN;break;case fi.DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchStartDollyRotate(n),this.state=ht.TOUCH_DOLLY_ROTATE;break;default:this.state=ht.NONE}break;default:this.state=ht.NONE}this.state!==ht.NONE&&this.dispatchEvent(Ec)}function R0(n){switch(this._trackPointer(n),this.state){case ht.TOUCH_ROTATE:if(this.enableRotate===!1)return;this._handleTouchMoveRotate(n),this.update();break;case ht.TOUCH_PAN:if(this.enablePan===!1)return;this._handleTouchMovePan(n),this.update();break;case ht.TOUCH_DOLLY_PAN:if(this.enableZoom===!1&&this.enablePan===!1)return;this._handleTouchMoveDollyPan(n),this.update();break;case ht.TOUCH_DOLLY_ROTATE:if(this.enableZoom===!1&&this.enableRotate===!1)return;this._handleTouchMoveDollyRotate(n),this.update();break;default:this.state=ht.NONE}}function P0(n){this.enabled!==!1&&n.preventDefault()}function I0(n){n.key==="Control"&&(this._controlActive=!0,this.domElement.getRootNode().addEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}function N0(n){n.key==="Control"&&(this._controlActive=!1,this.domElement.getRootNode().removeEventListener("keyup",this._interceptControlUp,{passive:!0,capture:!0}))}var ko=class extends Ni{constructor(e){super(e)}load(e,t,i,s){let r=this,a=new xr(this.manager);a.setPath(this.path),a.setResponseType("arraybuffer"),a.setRequestHeader(this.requestHeader),a.setWithCredentials(this.withCredentials),a.load(e,function(o){try{t(r.parse(o))}catch(c){s?s(c):console.error(c),r.manager.itemError(e)}},i,s)}parse(e){function t(l){let u=new DataView(l),h=32/8*3+32/8*3*3+16/8,d=u.getUint32(80,!0);if(80+32/8+d*h===u.byteLength)return!0;let g=[115,111,108,105,100];for(let x=0;x<5;x++)if(i(g,u,x))return!1;return!0}function i(l,u,h){for(let d=0,f=l.length;d<f;d++)if(l[d]!==u.getUint8(h+d))return!1;return!0}function s(l){let u=new DataView(l),h=u.getUint32(80,!0),d,f,g,x=!1,m,p,T,M,y;for(let C=0;C<70;C++)u.getUint32(C,!1)==1129270351&&u.getUint8(C+4)==82&&u.getUint8(C+5)==61&&(x=!0,m=new Float32Array(h*3*3),p=u.getUint8(C+6)/255,T=u.getUint8(C+7)/255,M=u.getUint8(C+8)/255,y=u.getUint8(C+9)/255);let R=84,E=50,P=new cn,D=new Float32Array(h*3*3),b=new Float32Array(h*3*3),w=new qe;for(let C=0;C<h;C++){let k=R+C*E,G=u.getFloat32(k,!0),q=u.getFloat32(k+4,!0),X=u.getFloat32(k+8,!0);if(x){let V=u.getUint16(k+48,!0);(V&32768)===0?(d=(V&31)/31,f=(V>>5&31)/31,g=(V>>10&31)/31):(d=p,f=T,g=M)}for(let V=1;V<=3;V++){let te=k+V*12,U=C*3*3+(V-1)*3;D[U]=u.getFloat32(te,!0),D[U+1]=u.getFloat32(te+4,!0),D[U+2]=u.getFloat32(te+8,!0),b[U]=G,b[U+1]=q,b[U+2]=X,x&&(w.setRGB(d,f,g,It),m[U]=w.r,m[U+1]=w.g,m[U+2]=w.b)}}return P.setAttribute("position",new Nt(D,3)),P.setAttribute("normal",new Nt(b,3)),x&&(P.setAttribute("color",new Nt(m,3)),P.hasColors=!0,P.alpha=y),P}function r(l){let u=new cn,h=/solid([\s\S]*?)endsolid/g,d=/facet([\s\S]*?)endfacet/g,f=/solid\s(.+)/,g=0,x=/[\s]+([+-]?(?:\d*)(?:\.\d*)?(?:[eE][+-]?\d+)?)/.source,m=new RegExp("vertex"+x+x+x,"g"),p=new RegExp("normal"+x+x+x,"g"),T=[],M=[],y=[],R=new N,E,P=0,D=0,b=0;for(;(E=h.exec(l))!==null;){D=b;let w=E[0],C=(E=f.exec(w))!==null?E[1]:"";for(y.push(C);(E=d.exec(w))!==null;){let q=0,X=0,V=E[0];for(;(E=p.exec(V))!==null;)R.x=parseFloat(E[1]),R.y=parseFloat(E[2]),R.z=parseFloat(E[3]),X++;for(;(E=m.exec(V))!==null;)T.push(parseFloat(E[1]),parseFloat(E[2]),parseFloat(E[3])),M.push(R.x,R.y,R.z),q++,b++;X!==1&&console.error("THREE.STLLoader: Something isn't right with the normal of face number "+g),q!==3&&console.error("THREE.STLLoader: Something isn't right with the vertices of face number "+g),g++}let k=D,G=b-D;u.userData.groupNames=y,u.addGroup(k,G,P),P++}return u.setAttribute("position",new Gt(T,3)),u.setAttribute("normal",new Gt(M,3)),u}function a(l){return typeof l!="string"?new TextDecoder().decode(l):l}function o(l){if(typeof l=="string"){let u=new Uint8Array(l.length);for(let h=0;h<l.length;h++)u[h]=l.charCodeAt(h)&255;return u.buffer||u}else return l}let c=o(e);return t(c)?s(c):r(a(e))}};var yn=256,Ac=1.6,vd=6;function Cc(n,e="#888888"){try{let t=document.createElement("canvas");t.width=t.height=1;let i=t.getContext("2d",{willReadFrequently:!0});if(!i||!n)return e;i.fillStyle=e,i.fillStyle=n,i.fillRect(0,0,1,1);let[s,r,a]=i.getImageData(0,0,1,1).data;return`#${[s,r,a].map(o=>o.toString(16).padStart(2,"0")).join("")}`}catch{return e}}function D0(n){let e=new qe(n),t={h:0,s:0,l:0};e.getHSL(t);let i=Math.min(.82,Math.max(.075,t.l));return i===t.l?n:(e.setHSL(t.h,t.s,i),`#${e.getHexString()}`)}function Rc(n,e){let t=getComputedStyle(n),i=(s,r)=>t.getPropertyValue(s).trim()||r;return{part:D0(e||Cc(i("--ui-accent","#4f7cff"),"#4f7cff")),plate:Cc(i("--w-plate","#75695a"),"#75695a"),bed:Cc(i("--w-bed","#26272b"),"#26272b")}}function L0(){let e=1024/yn,t=document.createElement("canvas");t.width=t.height=1024;let i=t.getContext("2d");if(i){let r=document.createElement("canvas");r.width=r.height=128;let a=r.getContext("2d");if(a){let l=a.createImageData(128,128);for(let h=0;h<l.data.length;h+=4){let d=196+Math.floor(Math.random()*44);l.data[h]=l.data[h+1]=l.data[h+2]=d,l.data[h+3]=255}a.putImageData(l,0,0);let u=i.createPattern(r,"repeat");u&&(i.fillStyle=u,i.fillRect(0,0,1024,1024))}let o=(l,u,h)=>{i.fillStyle=`rgba(255,255,255,${u})`;let d=Math.round(l*e-h/2);i.fillRect(d,0,h,1024),i.fillRect(0,d,1024,h)};for(let l=16;l<yn;l+=16)o(l,l%64===0?.5:.24,l%64===0?3:2);i.strokeStyle="rgba(255,255,255,0.42)",i.lineWidth=3;let c=4*e;i.strokeRect(c,c,1024-c*2,1024-c*2)}let s=new sr(t);return s.colorSpace=It,s.anisotropy=8,s.repeat.set(1/yn,1/yn),s.offset.set(.5,.5),s}function U0(n,e){let t=n/2,i=new _s;return i.moveTo(-t+e,-t),i.lineTo(t-e,-t),i.quadraticCurveTo(t,-t,t,-t+e),i.lineTo(t,t-e),i.quadraticCurveTo(t,t,t-e,t),i.lineTo(-t+e,t),i.quadraticCurveTo(-t,t,-t,t-e),i.lineTo(-t,-t+e),i.quadraticCurveTo(-t,-t,-t+e,-t),i}function Pc(){try{return window.matchMedia("(prefers-reduced-motion: reduce)").matches}catch{return!1}}function yd(n,e){let t=new Lo({antialias:!0,alpha:!0,preserveDrawingBuffer:!1});t.setPixelRatio(Math.min(window.devicePixelRatio||1,2)),t.outputColorSpace=It,t.setClearColor(0,0);let i=t.domElement;Object.assign(i.style,{display:"block",width:"100%",height:"100%",outline:"none",touchAction:"none"}),i.setAttribute("aria-label","3D view of the part. Drag or use the arrow keys to turn, scroll or use plus and minus to zoom."),i.setAttribute("role","img"),i.tabIndex=0,n.appendChild(i),t.shadowMap.enabled=!0,t.shadowMap.type=ka;let s=new ir;s.add(new yr(16777215,5919046,1.15));let r=new Di(16774114,2.3);r.castShadow=!0,r.shadow.mapSize.set(1024,1024),r.shadow.bias=-5e-4,r.shadow.normalBias=.4,s.add(r),s.add(r.target);let a=new Di(14542847,.65);a.position.set(220,110,160),s.add(a);let o=new Di(16777215,.85);o.position.set(80,150,-240),s.add(o);let c=new N(-.42,1,.5).normalize(),l=(U,Q)=>{let he=Math.max(Q*1.8,24);r.position.copy(U).addScaledVector(c,he*4),r.target.position.copy(U);let ue=r.shadow.camera;ue.left=ue.bottom=-he,ue.right=ue.top=he,ue.near=1,ue.far=he*9,ue.updateProjectionMatrix()};l(new N,60);let u=L0(),h=new mr(U0(yn,5),{depth:Ac,bevelEnabled:!1,curveSegments:6});h.rotateX(-Math.PI/2),h.translate(0,-Ac,0);let d=new li({color:e.plate,map:u,bumpMap:u,bumpScale:.35,roughness:.92,metalness:.12}),f=new li({color:e.plate,roughness:.6,metalness:.5}),g=new Ot(h,[d,f]);g.receiveShadow=!0,s.add(g);let x=new li({color:e.bed,roughness:.75,metalness:.2}),m=new Ot(new oi(yn+8,vd,yn+8),x);m.position.y=-Ac-vd/2,s.add(m);let p=new Ut(30,1,.5,5e3);p.position.set(140,190,240);let T=new Oo(p,i);T.enableDamping=!0,T.dampingFactor=.12,T.autoRotate=!Pc(),T.autoRotateSpeed=.8,T.maxPolarAngle=Math.PI*.495;let M=()=>{T.autoRotate=!1};T.addEventListener("start",M);let y=U=>{let he={ArrowLeft:[-.2,0,1],ArrowRight:[.2,0,1],ArrowUp:[0,-.12,1],ArrowDown:[0,.12,1],"+":[0,0,.87],"=":[0,0,.87],"-":[0,0,1.15]}[U.key];if(!he||U.altKey||U.ctrlKey||U.metaKey)return;U.preventDefault(),T.autoRotate=!1;let ue=new ui().setFromVector3(p.position.clone().sub(T.target));ue.theta+=he[0],ue.phi=Math.min(T.maxPolarAngle,Math.max(.08,ue.phi+he[1])),ue.radius=Math.min(T.maxDistance,Math.max(T.minDistance,ue.radius*he[2])),p.position.copy(T.target).add(new N().setFromSpherical(ue)),T.update(),D=!0};i.addEventListener("keydown",y);let R=new li({color:e.part,roughness:.5,metalness:.02}),E=null,P={pos:p.position.clone(),target:new N},D=!0,b=0,w=!1,C=!0,k=()=>{let U=Math.max(1,n.clientWidth),Q=Math.max(1,n.clientHeight);t.setSize(U,Q,!1),p.aspect=U/Q,p.updateProjectionMatrix(),D=!0},G=new ResizeObserver(k);G.observe(n),k();let q=new IntersectionObserver(U=>{C=U.some(Q=>Q.isIntersecting),D=!0});q.observe(n);let X=()=>{D=!0};T.addEventListener("change",X);let V=()=>{if(w||(b=requestAnimationFrame(V),!C||document.hidden))return;(T.update()||D)&&(D=!1,t.render(s,p))};V();let te=U=>{let Q=Math.max(U.x,U.y,U.z,10),he=Math.max(U.length()/2,5),ue=p.fov*Math.PI/180,ze=2*Math.atan(Math.tan(ue/2)*p.aspect),je=he/Math.sin(Math.min(ue,ze)/2)*1.18,Qe=new N(0,U.y/2,0);p.near=Math.max(.1,Q/200),p.far=Math.max(2e3,Q*40),p.position.copy(Qe).add(new N(.5,1.12,1).normalize().multiplyScalar(je)),p.updateProjectionMatrix(),T.target.copy(Qe),T.minDistance=Q*.4,T.maxDistance=Math.max(yn*2.2,je*3),T.update(),l(Qe,he),P={pos:p.position.clone(),target:Qe.clone()}};return{load(U){let Q=new ko().parse(U);Q.rotateX(-Math.PI/2),Q.computeBoundingBox();let he=Q.boundingBox??new Tn,ue=he.getSize(new N),ze=he.getCenter(new N);Q.translate(-ze.x,-he.min.y,-ze.z),Q.getAttribute("normal")||Q.computeVertexNormals(),E&&(s.remove(E),E.geometry.dispose()),E=new Ot(Q,R),E.castShadow=!0,E.receiveShadow=!0,s.add(E),te(ue),D=!0;let je=(Q.index?Q.index.count:Q.getAttribute("position").count)/3,Qe=[ue.x,ue.z,ue.y];return{triangles:je,size:Qe,fitsBed:Qe[0]<=yn&&Qe[1]<=yn&&Qe[2]<=yn}},setColors(U){U.part&&(R.color=new qe(U.part)),U.plate&&(d.color=new qe(U.plate),f.color=new qe(U.plate)),U.bed&&(x.color=new qe(U.bed)),D=!0},setAutoRotate(U){T.autoRotate=U,D=!0},resetView(){p.position.copy(P.pos),T.target.copy(P.target),T.update(),D=!0},dispose(){w=!0,cancelAnimationFrame(b),G.disconnect(),q.disconnect(),T.removeEventListener("change",X),T.removeEventListener("start",M),i.removeEventListener("keydown",y),T.dispose(),E?.geometry.dispose(),R.dispose(),h.dispose(),u.dispose(),d.dispose(),f.dispose(),m.geometry.dispose(),x.dispose(),r.shadow.map?.dispose(),t.dispose(),t.forceContextLoss(),i.remove()}}}function wd(n){let e=n.indexOf(","),t=atob(n.slice(e+1)),i=new Uint8Array(t.length);for(let s=0;s<t.length;s+=1)i[s]=t.charCodeAt(s);return i.buffer}import{Fragment as Sd,jsx as Tt,jsxs as gi}from"react/jsx-runtime";var k0=typeof Ic.useTheme=="function"?Ic.useTheme:()=>null,B0=n=>n.map(e=>e>=100?Math.round(e):Math.round(e*10)/10).join(" \xD7 ")+" mm";function Hi({rest:n,stl:e,preview:t,still:i=null,color:s,label:r,autoMount:a=!1,className:o=""}){let c=F0(),u=O0(Jn.subscribe,Jn.holder,Jn.holder)===c&&!!e,[h,d]=Bo(null),f=g=>d(z0(g.currentTarget));return As(()=>d(null),[i,t]),As(()=>{a&&e&&Jn.claim(c)},[a,e,c]),As(()=>()=>Jn.release(c),[c]),Tt("div",{className:`w-media ${o}`,"data-workshop-viewer":u?"live":"still",style:!u&&h?{background:h}:void 0,children:u&&e?Tt(V0,{rest:n,stl:e,color:s,label:r,onClose:()=>Jn.release(c)}):gi(Sd,{children:[i?Tt("img",{className:"fill",src:i,alt:`Preview of ${r}`,draggable:!1,onLoad:f}):t?Tt(Un,{rest:n,fileRef:t,alt:`Preview of ${r}`,className:"fill",fallback:Tt(Md,{}),onLoad:f}):Tt(Md,{}),e?Tt("div",{className:"over br",children:gi("button",{type:"button",className:"w-view3d",onClick:()=>Jn.claim(c),"data-workshop-view3d":"",children:[Tt(Ie,{name:"cube"})," View in 3D"]})}):null]})})}function z0(n){try{let e=document.createElement("canvas");e.width=e.height=1;let t=e.getContext("2d",{willReadFrequently:!0});if(!t)return null;t.drawImage(n,0,0,1,1,0,0,1,1);let[i,s,r,a]=t.getImageData(0,0,1,1).data;return a===255?`rgb(${i}, ${s}, ${r})`:null}catch{return null}}function Md(){return gi("div",{className:"center",children:[Tt(Ie,{name:"cube",size:28}),Tt("span",{children:"No picture of this part"})]})}function V0({rest:n,stl:e,color:t,label:i,onClose:s}){let r=bd(null),a=bd(null),[o,c]=Bo(null),[l,u]=Bo(null),[h,d]=Bo(()=>!Pc()),{file:f,error:g,loading:x}=Or(n,e),m=k0();As(()=>{let T=r.current;if(!T)return;try{a.current=yd(T,Rc(T,t))}catch{c("3D is not available in this window (no WebGL).");return}let M=a.current,y=()=>d(!1),R=E=>{/^Arrow|^[+=-]$/.test(E.key)&&d(!1)};return T.addEventListener("pointerdown",y),T.addEventListener("keydown",R),T.addEventListener("wheel",y,{passive:!0}),()=>{T.removeEventListener("pointerdown",y),T.removeEventListener("keydown",R),T.removeEventListener("wheel",y),M.dispose(),a.current=null}},[]),As(()=>{if(!(!f?.dataUrl||!a.current))try{u(a.current.load(wd(f.dataUrl)))}catch{c("This file is not a readable STL.")}},[f]),As(()=>{r.current&&a.current&&a.current.setColors(Rc(r.current,t))},[m,t]);let p=o||(g?"Could not load the model from the workshop.":null);return gi(Sd,{children:[Tt("div",{ref:r,className:"stage",tabIndex:-1}),p?gi("div",{className:"center",children:[Tt(Ie,{name:"alert",size:22}),Tt("span",{children:p})]}):x||!l?gi("div",{className:"center",children:[Tt(Fn,{}),Tt("span",{children:"Loading the part\u2026"})]}):null,l?Tt("div",{className:"over bl",children:gi("span",{className:"w-glass num",title:`${l.triangles.toLocaleString()} triangles`,children:[B0(l.size),l.fitsBed?"":" \xB7 too big for the bed"]})}):null,gi("div",{className:"over tr",children:[l?Tt("button",{type:"button",className:"w-glass",onClick:()=>{a.current?.resetView(),a.current?.setAutoRotate(!h),d(!h)},"aria-label":h?"Stop turning":"Reset the view and turn slowly",title:h?"Stop turning":"Reset view",children:Tt(Ie,{name:h?"pause":"reset",size:12})}):null,Tt("button",{type:"button",className:"w-glass",onClick:s,"aria-label":`Close the 3D view of ${i}`,title:"Back to the picture",children:Tt(Ie,{name:"x",size:12})})]})]})}import{Fragment as Ad,jsx as Pn,jsxs as Pr}from"react/jsx-runtime";function Ed({props:n,rest:e,path:t}){let{file:i,args:s,result:r,fallback:a}=n,o=vh(r,s),c=i?.kind==="image"||/^image\//.test(i?.mime||"")||/\.png$/i.test(i?.path||"");return!o||!c||!yh(o,i.path)?Pn(Ad,{children:a}):Pn(W0,{call:o,file:i,rest:e,path:t,fallback:a})}function W0({call:n,file:e,rest:t,path:i,fallback:s}){let[r,a]=Td(null),[o,c]=Td(!1);G0(()=>{let f=!0;return e.resolveUrl().then(g=>f&&a(g),()=>f&&c(!0)),()=>{f=!1}},[e]);let{ov:l}=Xi(t,!1),u=l?wh(l.designs,n.slug,n.version):null;if(o)return Pn(Ad,{children:s});let h=bh(n),d=l?.designs.find(f=>f.slug===n.slug)?.title||n.slug.replace(/[_-]+/g," ");return Pr("div",{className:"h3w w-card","data-workshop-design-card":"",children:[Pn(Yi,{}),Pr("div",{className:"head",children:[Pn(Ie,{name:"cube"}),Pn("span",{className:"name",children:d}),Pr(Nn,{tone:"accent",children:["v",n.version]}),Pr("button",{type:"button",className:"w-link",style:{marginLeft:"auto",fontSize:12},onClick:()=>H0.navigate(i),children:["All versions ",Pn(Ie,{name:"arrow",size:12})]})]}),Pn(Hi,{rest:t,stl:u?.stl??null,preview:null,still:r,color:null,label:`${d} v${n.version}`}),h.length||n.warnings.length?Pr("div",{className:"w-facts-line num",children:[h.map(f=>Pn("span",{className:f.includes("too big")?"bad":void 0,children:f},f)),n.warnings.map(f=>Pn("span",{className:"warn",title:f,children:f.length>60?`${f.slice(0,57)}\u2026`:f},f))]}):null]})}import{useState as ev}from"react";import{useState as zo}from"react";import{Fragment as _i,jsx as j,jsxs as _e}from"react/jsx-runtime";function Cd({ov:n,rest:e,nowSec:t}){let i=Wc(n),s=kr();return _e("section",{className:"w-hero","aria-label":"Printer now","data-workshop-hero":i,children:[j(X0,{ov:n,action:s,rest:e,nowSec:t,showCam:i==="approve",brief:i==="running"}),j(Br,{state:s}),i==="approve"?j(q0,{ov:n,rest:e,nowSec:t,action:s}):i==="running"?j(Z0,{ov:n,rest:e,nowSec:t}):i==="attention"?j(K0,{ov:n,rest:e,nowSec:t}):i==="offline"?j(j0,{ov:n}):j(J0,{ov:n,rest:e,nowSec:t})]})}function X0({ov:n,action:e,rest:t,nowSec:i,showCam:s,brief:r}){let a=n.printer,[o,c]=zo(!1),[l,u]=zo(!1),h=s&&n.camera.available&&n.camera.frame?n.camera.frame:null,d=Kt(n.camera.taken_ts,i),f=Fr(a.state),g=Ps(a),x=n.now?.name||a.job_name,m=n.viewer.is_owner,p=m?void 0:n.viewer.reason||"Only the printer owner can do this.",T=n.waiting.some(M=>M.action==="resume");return _e(_i,{children:[_e("div",{className:"w-strip",children:[h?j("button",{type:"button",className:"w-camthumb",onClick:()=>u(M=>!M),"aria-expanded":l,"aria-label":`Camera picture${d?`, ${d}`:""}: ${l?"hide":"show larger"}`,title:`Camera${d?`, ${d}`:""}`,"data-workshop-camthumb":"",children:j(Un,{rest:t,fileRef:h,alt:"",fallback:j(Ie,{name:"camera"})})}):null,_e("span",{className:`w-state t-${Hc(a.state)}${a.state==="printing"?" live":""}`,"data-workshop-state":a.state,children:[j("span",{className:"dot","aria-hidden":!0}),Vc(a.state)]}),x&&!r?_e("span",{className:"w-strip-job",children:[j("span",{className:"name ellipsis",children:x}),n.now?_e("span",{className:"faint w-for",children:["for ",j(Dn,{p:n.now.for,groups:n.groups})]}):null]}):j("span",{className:"w-strip-job"}),r?null:f?_e("span",{className:"w-strip-meta num",children:[_e("span",{children:[g,"%"]}),bn(a.remaining_min)?_e("span",{children:[j(Ie,{name:"clock",size:12}),bn(a.remaining_min)," left"]}):null,a.layer!==null&&a.total_layers?_e("span",{children:[j(Ie,{name:"layers",size:12}),a.layer,"/",a.total_layers]}):null]}):a.bed_temp!==null?j("span",{className:"w-strip-meta num",children:_e("span",{title:"Bed temperature",children:[j(Ie,{name:"thermo",size:12}),Math.round(a.bed_temp)," \xB0C"]})}):null,f?_e("span",{className:"w-strip-actions",children:[a.state==="printing"?_e("button",{type:"button",className:"w-btn",disabled:!!e.busy||!m,title:p??"Pause: the printer holds where it is; you can resume from here.",onClick:()=>{e.run("home3d pause")},"data-workshop-action":"pause",children:[e.busy==="home3d pause"?j(Fn,{}):j(Ie,{name:"pause",size:12})," Pause"]}):T?null:_e("button",{type:"button",className:"w-btn",disabled:!!e.busy||!m,title:p??"Resume the print from where it stopped.",onClick:()=>{e.run("home3d approve resume")},"data-workshop-action":"resume",children:[e.busy==="home3d approve resume"?j(Fn,{}):j(Ie,{name:"play",size:12})," Resume"]}),_e("button",{type:"button",className:"w-btn danger",disabled:!!e.busy||!m,title:p??"Stop the print (asks first)","aria-expanded":o,onClick:()=>c(M=>!M),"data-workshop-action":"stop",children:[j(Ie,{name:"stop",size:12})," Stop"]})]}):null]}),f&&!r?j("div",{className:"w-strip-bar",role:"progressbar","aria-label":"Print progress","aria-valuenow":g,"aria-valuemin":0,"aria-valuemax":100,children:j("i",{style:{width:`${g}%`}})}):null,h&&l?j("div",{style:{padding:"0 20px 16px",maxWidth:560},children:j(Vo,{ov:n,rest:t,nowSec:i,fallback:null})}):null,o&&f?j("div",{style:{padding:"0 20px 16px"},children:_e("div",{className:"w-confirm",role:"alertdialog","aria-labelledby":"w-stop-q",children:[_e("p",{id:"w-stop-q",children:[_e("b",{children:["Stop \u201C",x||"this print","\u201D now?"]})," ",_e("span",{className:"muted",children:["The printer cancels the job",n.now?` for ${Wi(n.now.for)}`:"",". The unfinished part stays on the plate, and the job cannot be resumed."]})]}),_e("div",{className:"row",children:[_e("button",{type:"button",className:"w-btn danger-solid",autoFocus:!0,disabled:!!e.busy,onClick:()=>{c(!1),e.run("home3d stop")},"data-workshop-action":"stop-confirm",children:[j(Ie,{name:"stop",size:12})," Yes, stop the print"]}),j("button",{type:"button",className:"w-btn",onClick:()=>c(!1),children:"Keep printing"}),j("span",{className:"w-cmd",style:{alignSelf:"center"},children:"runs /home3d stop"})]})]})}):null,a.errors.length?j("div",{style:{padding:"0 20px 12px"},children:a.errors.map((M,y)=>_e("div",{className:"w-banner t-bad",style:{marginBottom:6},children:[j(Ie,{name:"alert"}),_e("span",{children:[j("b",{children:M.text||"Printer error"})," ",M.code?j("span",{className:"w-cmd",children:M.code}):null]})]},`${M.code}-${y}`))}):null]})}function q0({ov:n,rest:e,nowSec:t,action:i}){let[s,r]=zo(0),a=Math.min(s,n.waiting.length-1),o=n.waiting[a];return _e(_i,{children:[n.waiting.length>1?_e("div",{className:"w-tabs",children:[_e("span",{className:"w-tabs-label",id:"w-tabs-label",children:[n.waiting.length," waiting for your OK"]}),j("div",{role:"group","aria-labelledby":"w-tabs-label",style:{display:"contents"},children:n.waiting.map((c,l)=>_e("button",{type:"button",className:"w-tab","aria-pressed":l===a,"aria-label":`${c.name||"Job"}, asked by ${Wi(c.asked_by)}`,title:`${c.name||"Job"}, asked by ${Wi(c.asked_by)}`,onClick:()=>r(l),children:[j(Ko,{p:c.asked_by,groups:n.groups,small:!0}),j("span",{className:"ellipsis",children:c.name||"Job"})]},`${c.action}-${c.queue_item_id??"x"}-${c.id}`))})]}):null,j(Y0,{w:o,ov:n,rest:e,nowSec:t,action:i},`${o.action}-${o.queue_item_id??"x"}-${o.id}`)]})}function Y0({w:n,ov:e,rest:t,nowSec:i,action:s}){let r=qc(n),a=Ns(n.checklist),o=$o(n),c=Yc(n),l=Ds(e.filament.slots,n.facts.slot),u=Zc(n.facts,e.filament.slots),h=s.busy===c,d=!!n.alt&&s.busy===n.alt.command,f=s.outcome?.kind==="ran"&&s.outcome.ok&&(s.outcome.command===c||s.outcome.command===n.alt?.command),g=e.viewer.is_owner,x=n.action==="start"?"Waiting for your OK":n.action==="clear"?"Plate check":"Paused, waiting for you",m=a.length?`${a.length} check${a.length>1?"s":""} not passed yet: the printer refuses until ${a.length>1?"they are":"it is"} fixed.`:"Not ready yet: the printer refuses for now.",p=Kt(n.asked_ts,i),T=n.request_text.trim(),M=n.asked_by.group.trim(),y=Jc(n.facts,e.filament.slots),R=[y.name,y.where.toLowerCase()].filter(Boolean).join(", "),E=n.checklist.length-a.length,[P,D]=zo(!1);return _e("div",{className:"w-hero-body","data-workshop-approval":n.id,children:[j(Hi,{rest:t,stl:n.model?.stl??null,preview:n.model?.preview??null,color:u,label:n.name||"the part",className:"tall",autoMount:!0}),_e("div",{className:"w-ask",children:[_e("p",{className:"w-sender",children:[T?null:j("span",{className:"faint",children:"asked by"}),j(Ko,{p:n.asked_by,groups:e.groups}),j(Dn,{p:n.asked_by,groups:e.groups}),p?j("span",{className:"faint",children:p}):null]}),T?_e(_i,{children:[j("blockquote",{className:`w-bubble g-${M?Ls(e.groups,M):"other"}${T.length>140?" long":""}`,children:j("span",{className:`words${P?"":" clamped"}`,children:T})}),T.length>260?j("button",{type:"button",className:"w-link w-bubble-more","aria-expanded":P,onClick:()=>D(b=>!b),children:P?"Show less":"Show the whole request"}):null]}):null,_e("div",{className:"w-jobline",children:[j("h3",{className:T?"w-job":"w-big",children:n.name||"A print job"}),j(Nn,{tone:"accent",children:x})]}),n.action==="start"?_e("dl",{className:"w-spec",children:[j("dt",{children:"Print time"}),j("dd",{className:"num",children:bn(n.facts.print_time_min)||"Unknown"}),j("dt",{children:"Filament"}),_e("dd",{children:[u?j("span",{className:"w-swatch",style:{"--sw":u},"aria-hidden":!0}):null,j("span",{className:"num",children:n.facts.grams===null&&!y.material?"Not chosen yet":`${n.facts.grams!==null?`${Math.round(n.facts.grams*10)/10} g`:"Amount unknown,"} ${y.material?`${n.facts.grams!==null?"of ":""}${y.material}`:"of a material not chosen yet"}`}),R?j("span",{className:"more",children:R}):null]}),j("dt",{children:"When done"}),_e("dd",{title:n.facts.eject_reason||void 0,children:[j(Ie,{name:n.facts.eject_planned?"eject":"box",size:13}),j("span",{children:qo(n.facts.eject_planned)})]})]}):null,l&&l.remain_pct!==null&&n.facts.grams!==null&&l.remain_pct<15?_e("div",{className:"w-banner t-warn",style:{margin:"14px 0 0"},children:[j(Ie,{name:"spool"}),_e("span",{children:[jc(n.facts,e.filament.slots)," is down to ",l.remain_pct,"%: check there is enough for ",Math.round(n.facts.grams)," g."]})]}):null,n.checklist.length?_e(_i,{children:[_e("p",{className:`w-checks-sum t-${a.length?"bad":"good"}`,children:[j(Ie,{name:a.length?"alert":"check"}),a.length?`${a.length} of ${n.checklist.length} checks not passed`:`All ${E} checks passed`]}),j("ul",{className:"w-checks","aria-label":"Safety checklist",children:n.checklist.map(b=>_e("li",{className:b.ok?"ok":"no",children:[j(Ie,{name:b.ok?"check":"x",title:b.ok?"passed":"not passed"}),_e("span",{children:[b.label,b.detail?j("span",{className:"detail",children:b.detail}):null]})]},b.id||b.label))})]}):null,_e("div",{className:"w-go",children:[_e("button",{type:"button",className:`w-btn primary${o?"":" muted-primary"}`,disabled:!!s.busy||!c||f||!g,onClick:()=>{s.run(c)},"data-workshop-action":`approve-${n.action}`,children:[h?j(Fn,{}):j(Ie,{name:n.action==="clear"?"check":"play",size:13}),h?"Sending\u2026":f?"Sent":r.button]}),n.alt?_e("button",{type:"button",className:"w-btn",disabled:!!s.busy||f||!g,onClick:()=>{s.run(n.alt.command)},title:`runs /${n.alt.command}`,"data-workshop-action":"approve-alt",children:[d?j(Fn,{}):null,n.alt.label]}):null,_e("span",{className:"w-go-explain",children:[g?o?r.explain:m:e.viewer.reason||"Only the printer owner can approve.",j("br",{}),_e("span",{className:"w-cmd",children:["runs /",c]})]})]})]})]})}function Vo({ov:n,rest:e,nowSec:t,fallback:i}){let s=n.camera;if(!s.available||!s.frame)return j(_i,{children:i});let r=Kt(s.taken_ts,t);return _e("div",{className:"w-media wide","data-workshop-camera":"",children:[j(Un,{rest:e,fileRef:s.frame,alt:"Latest picture from the printer camera",className:"fill cover",fallback:i}),j("div",{className:"over bl",children:_e("span",{className:"w-photo-cap",children:[j(Ie,{name:"camera",size:12})," Camera",r?`, ${r}`:""]})})]})}function $0({ov:n}){return j("div",{className:"w-media wide",children:_e("div",{className:"center",children:[j(Ie,{name:"camera",size:26}),j("span",{children:n.camera.note||(n.camera.available?"No camera picture yet":"No camera on this printer")})]})})}function Z0({ov:n,rest:e,nowSec:t}){let i=n.printer,s=Ps(i),r=bn(i.remaining_min),a=i.remaining_min!==null&&i.state==="printing"?new Date((t+i.remaining_min*60)*1e3).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"}):"",o=Gc(n),c=n.now?.model,l=c?j(Hi,{rest:e,stl:c.stl,preview:c.preview,color:null,label:n.now?.name||"the part",className:"wide"}):j($0,{ov:n});return _e("div",{className:"w-hero-body",children:[j(Vo,{ov:n,rest:e,nowSec:t,fallback:l}),_e("div",{className:"w-run",children:[j("h3",{className:"w-big",children:n.now?.name||i.job_name||"A print job"}),n.now?_e("p",{className:"w-asked",children:[j("span",{children:"for"})," ",j(Dn,{p:n.now.for,groups:n.groups})]}):null,_e("div",{className:"w-pct num",children:[s,j("small",{children:"%"})]}),j("div",{className:"w-bigbar",role:"progressbar","aria-label":"Print progress","aria-valuenow":s,"aria-valuemin":0,"aria-valuemax":100,children:j("i",{style:{width:`${s}%`}})}),_e("div",{className:"w-lines num",children:[r?_e("div",{children:[j(Ie,{name:"clock"}),_e("span",{children:[j("b",{children:r})," left",a?`, done around ${a}`:""]})]}):null,i.layer!==null&&i.total_layers?_e("div",{children:[j(Ie,{name:"layers"}),_e("span",{children:["Layer ",j("b",{children:i.layer})," of ",i.total_layers]})]}):null,n.now?_e("div",{children:[j(Ie,{name:n.now.eject_planned?"eject":"box"}),j("span",{children:qo(n.now.eject_planned)})]}):null,i.bed_temp!==null?_e("div",{children:[j(Ie,{name:"thermo"}),_e("span",{children:["Bed ",Math.round(i.bed_temp)," \xB0C"]})]}):null]}),o.length?_e("div",{className:"w-banner t-accent",style:{marginTop:18,marginBottom:0},"data-workshop-after-print":"",children:[j(Ie,{name:"hand"}),_e("span",{children:[j("b",{children:"Waiting for your OK after this print:"})," ",o.map((u,h)=>_e("span",{children:[h?", ":"",u.name||"a job",u.asked_by.name?_e("span",{className:"muted",children:[" ","for ",j(Dn,{p:u.asked_by,groups:n.groups})]}):null,Ns(u.checklist).length?_e("span",{className:"muted",children:[" ","(",Ns(u.checklist).length," check",Ns(u.checklist).length>1?"s":""," not passed yet)"]}):null]},`${u.action}-${u.queue_item_id??h}`))]})]}):null]})]})}function J0({ov:n,rest:e,nowSec:t}){let i=n.queue[0],s=n.printer.state==="finished";return _e("div",{className:"w-idle",children:[_e("div",{children:[j("h3",{className:"w-big",children:s?`${n.now?.name||n.printer.job_name||"The last job"} is done.`:"Nothing is printing, and nothing is waiting for you."}),j("p",{className:"muted",style:{marginTop:6},children:i?_e(_i,{children:["Next in line: ",j("b",{children:i.name})," for ",j(Dn,{p:i.for,groups:n.groups}),i.status?_e("span",{className:"faint",children:[", ",i.status]}):null]}):_e(_i,{children:["When someone asks ",n.persona||"the printer"," for a part in a chat, it shows up here for your OK."]})})]}),n.camera.available&&n.camera.frame?j(Vo,{ov:n,rest:e,nowSec:t,fallback:null}):null]})}function K0({ov:n,rest:e,nowSec:t}){let i=n.printer,s=i.state==="failed"?`${n.now?.name||i.job_name||"The print"} failed.`:i.awaiting_plate_clear?"The plate needs clearing before the next print.":"The printer reports a problem.";return _e("div",{className:"w-idle",children:[_e("div",{children:[j("h3",{className:"w-big",children:s}),j("p",{className:"muted",style:{marginTop:6},children:i.awaiting_plate_clear?"Take the part off the bed. When the plate is empty, the request to continue shows up here.":"Check the printer and the camera picture. The people who asked have been told what happened."})]}),j(Vo,{ov:n,rest:e,nowSec:t,fallback:null})]})}function j0({ov:n}){let e=n.setup.checks.find(t=>t.status==="error"||t.status==="missing");return j("div",{className:"w-idle",children:_e("div",{children:[j("h3",{className:"w-big",children:"The printer is not answering."}),j("p",{className:"muted",style:{marginTop:6},children:e?_e(_i,{children:[e.label,": ",e.detail,/[.!?]$/.test(e.detail.trim())?"":".",e.fix?_e("span",{className:"w-fix",style:{fontSize:13},children:[j("b",{children:"Fix:"}),j(zr,{text:e.fix})]}):null]}):"Check that the printer is on and on the network. The Health list below shows what the workshop can reach."})]})})}import{useState as Rd}from"react";import{Fragment as Id,jsx as ie,jsxs as De}from"react/jsx-runtime";var Nc=n=>/^printing$|^running$/i.test(n.trim());function Nd({ov:n,rest:e}){let t=n.queue.findIndex(i=>!Nc(i.status));return ie(Zn,{id:"queue",title:"Up next",count:n.queue.length,children:n.queue.length?ie("ol",{className:"w-rows","aria-label":"Print queue",children:n.queue.map((i,s)=>De("li",{className:`w-row${s===t?" next":""}`,children:[ie("span",{className:"w-pos num","aria-label":`Position ${s+1}`,children:s+1}),ie(gh,{rest:e,fileRef:i.model?.preview??null,alt:`Preview of ${i.name}`}),De("div",{className:"w-main",children:[De("span",{className:"title",children:[ie("span",{className:"ellipsis",children:i.name||"Untitled job"}),Nc(i.status)?n.printer.state==="printing"?ie(Nn,{tone:"accent",children:"Printing now"}):n.printer.state==="paused"?ie(Nn,{tone:"warn",children:"Paused"}):n.printer.state==="failed"?ie(Nn,{tone:"bad",children:"Failed"}):null:null]}),De("span",{className:"sub",children:[i.for.name?De("span",{children:["for ",ie(Dn,{p:i.for,groups:n.groups})]}):ie("span",{children:"not asked in a chat"}),bn(i.print_time_min)?ie("span",{className:"num",children:bn(i.print_time_min)}):null,i.eject_planned!==null?ie("span",{children:i.eject_planned?"auto-eject":"stays on plate"}):null,i.ours?null:ie("span",{children:"from elsewhere"})]})]}),ie("div",{className:"end",children:i.status&&!Nc(i.status)?ie("span",{className:"state",children:Yo(i.status)}):null})]},i.id))}):ie(Ln,{children:"The queue is empty. New requests wait here after you approve them."})})}function Dd({ov:n,rest:e,nowSec:t}){let i=kr(),s=n.done_box.filter(r=>!r.collected).length;return De(Zn,{id:"done",title:"Done box",count:n.done_box.length,aside:s?De("span",{className:"faint",children:[s," to pick up"]}):null,children:[ie(Br,{state:i,inline:!0}),n.done_box.length?ie("ul",{className:"w-rows",children:n.done_box.map((r,a)=>{let o=$c(r),c=r.command||`home3d collected ${r.id}`;return De("li",{className:"w-row","data-workshop-part":r.id,children:[ie("span",{className:"w-thumb",style:{width:64,height:48},children:r.photo?ie(Un,{rest:e,fileRef:r.photo,alt:`Photo of ${r.name} after printing`,fallback:ie(Ie,{name:"camera"})}):ie(Ie,{name:"camera"})}),De("div",{className:"w-main",children:[De("span",{className:"title",children:[ie("span",{className:"ellipsis",children:r.name||"A print"}),ie(Nn,{tone:o.tone,children:o.text})]}),De("span",{className:"sub",children:[De("span",{children:["for ",ie(Dn,{p:r.for,groups:n.groups})]}),Kt(r.finished_ts,t)?De("span",{children:["finished ",Kt(r.finished_ts,t)]}):null,r.detail?ie("span",{className:"faint",children:r.detail}):null]})]}),ie("div",{className:"end",children:r.collected?null:De("button",{type:"button",className:"w-btn sm",disabled:!!i.busy,onClick:()=>{i.run(c)},"aria-label":`Picked up: ${r.name||"a print"}`,title:`Marks it as picked up (runs /${c})`,"data-workshop-action":"collected",children:[i.busy===c?ie(Fn,{}):ie(Ie,{name:"check",size:12})," Picked up"]})})]},r.id||`row-${a}`)})}):ie(Ln,{icon:"box",children:"Nothing has come off the printer yet. Finished parts are listed here with a photo."})]})}function Ld({ov:n}){let e=n.filament.slots;return ie(Zn,{id:"filament",title:"Filament",children:e.length?ie("div",{className:"w-slots",children:e.map(t=>{let i=Is(t.color),s=t.remain_pct!==null&&t.remain_pct<15;return t.loaded?De("div",{className:`w-slot${s?" low":""}`,style:{"--sw":i??void 0},title:[t.name,i].filter(Boolean).join(", ")||void 0,children:[ie(Pd,{pct:t.remain_pct}),ie("span",{className:"mat ellipsis",children:t.material||"Unknown material"}),De("span",{className:"sub num ellipsis",role:t.remain_pct!==null?"meter":void 0,"aria-label":t.remain_pct!==null?`${t.label} remaining`:void 0,"aria-valuenow":t.remain_pct??void 0,"aria-valuemin":t.remain_pct!==null?0:void 0,"aria-valuemax":t.remain_pct!==null?100:void 0,children:[t.label,t.remain_pct!==null?`, ${t.remain_pct}%${s?", low":""}`:""]}),t.name?ie("span",{className:"brand",children:t.name}):null]},t.slot):De("div",{className:"w-slot empty",children:[ie(Pd,{pct:null,empty:!0}),ie("span",{className:"mat faint",children:"Empty"}),ie("span",{className:"sub ellipsis",children:t.label})]},t.slot)})}):ie(Ln,{icon:"spool",children:"The printer has not reported its filament yet."})})}function Pd({pct:n,empty:e}){let s=n===null?.72:Math.max(0,Math.min(100,n))/100,r=7+(23.5-7)*s;return De("svg",{width:"60",height:"60",viewBox:"-27 -27 54 54","aria-hidden":!0,children:[ie("circle",{r:"26",className:"flange"}),e||r<=7+.5?null:De(Id,{children:[ie("circle",{r,className:"wound"}),r-7>6?ie("circle",{r:(r+7)/2,className:"turn"}):null]}),e?null:De(Id,{children:[ie("circle",{r:7,className:"hub"}),ie("circle",{r:"2.4",className:"hole"})]})]})}function Ud({ov:n,nowSec:e}){let t=n.notices,i=eh(t),s=t.recent.slice(0,4),r=t.recent.length-s.length;return De(Zn,{id:"notices",title:"Messages",children:[i.tone!=="neutral"?De("div",{className:`w-summary t-${i.tone}`,children:[ie(Ie,{name:i.tone==="good"?"check":"alert"}),i.text]}):null,s.length?ie("ul",{className:"w-rows",children:s.map((a,o)=>{let c=nh(a.status);return De("li",{className:"w-row",style:{alignItems:"flex-start",padding:"9px 0"},children:[ie("span",{className:`w-dot t-${c}`,"aria-hidden":!0}),De("div",{className:"w-main",children:[ie("span",{className:"clamp2",title:a.text||void 0,children:Qc(a)}),De("span",{className:"sub",children:[De("span",{children:["to ",a.to||"someone"]}),ie("span",{children:Kt(a.ts,e)}),ie("span",{className:`t-${c} w-ink`,children:th(a.status)}),a.error?ie("span",{className:"faint",children:a.error}):null]})]})]},`${a.ts}-${o}`)})}):null,r>0?De("p",{className:"faint",style:{fontSize:12,paddingTop:4},children:["and ",r," earlier"]}):null,s.length?null:ie(Ln,{icon:"bell",children:"No messages sent yet. When a print starts, finishes or fails, the people who asked are told, and it shows here."})]})}function Fd({ov:n,nowSec:e}){let t=n.needs_human.filter(a=>a.open),i=n.needs_human.filter(a=>!a.open),s=i.length,r=[...t.slice(0,5),...i.slice(0,Math.max(0,4-t.length))];return De(Zn,{id:"improve",title:"Where it needed you",count:t.length||null,children:[t.length?null:De(Ln,{children:["Nothing needs a person right now",s?` (${s} handled before)`:"","."]}),r.length?ie("ul",{className:"w-rows",children:r.map(a=>De("li",{className:"w-row",style:{alignItems:"flex-start"},"data-workshop-moment":a.open?"open":"handled",children:[ie("span",{className:`lead${a.open?" t-warn":""}`,children:ie(Ie,{name:"hand"})}),De("div",{className:"w-main",children:[ie("span",{className:a.open?void 0:"muted",children:a.text}),De("span",{className:"sub",children:[a.open?null:ie("span",{className:"faint",children:"Handled"}),a.job?ie("span",{children:a.job}):null,a.who?De("span",{children:["for ",a.who]}):null,ie("span",{children:Kt(a.ts,e)})]})]})]},a.id))}):null,De("div",{children:[ie("h3",{className:"w-subhead",children:"Proposed upgrades"}),n.upgrades.length?ie("ul",{className:"w-rows",children:n.upgrades.map(a=>De("li",{className:"w-row",style:{alignItems:"flex-start"},children:[ie("span",{className:"lead t-accent",children:ie(Ie,{name:"spark"})}),De("div",{className:"w-main",children:[ie("span",{className:"title",children:ie("span",{children:a.title})}),a.why?ie("span",{className:"muted clamp3",children:a.why}):null,De("span",{className:"sub",children:[a.status?ie("span",{className:a.status==="done"?"t-good w-ink":"faint",children:Yo(a.status)}):null,a.count?De("span",{className:"num",children:["came up ",a.count,"\xD7"]}):null,a.model_ref?De("a",{className:"w-link",href:a.model_ref,target:"_blank",rel:"noreferrer noopener",children:[ie(Ie,{name:"link",size:12})," The printable part"]}):null]})]})]},a.id))}):ie(Ln,{icon:"spark",children:"No upgrade proposals yet. They come from patterns in the moments above."})]})]})}function Od({ov:n,rest:e}){return ie(Zn,{id:"designs",title:"Design versions",count:n.designs.length,children:n.designs.length?ie("div",{children:n.designs.map(t=>ie(Q0,{d:t,rest:e},t.slug))}):ie(Ln,{icon:"cube",children:"No designs yet. Ask the printer in a chat to design a part, and every version appears here."})})}function Q0({d:n,rest:e}){let[t,i]=Rd(null),[s,r]=Rd(0),a=n.versions[n.versions.length-1],o=n.versions.find(u=>u.version===t)??a;if(!o)return null;let c=ah(o.facts),l=o.previews[Math.min(s,o.previews.length-1)]??null;return De("div",{className:"w-design","data-workshop-design":n.slug,children:[De("div",{className:"w-design-head",children:[ie("span",{style:{fontWeight:650},children:n.title}),ie("div",{className:"w-vers",role:"group","aria-label":`Versions of ${n.title}`,children:n.versions.map(u=>De("button",{type:"button",className:"w-ver num","aria-pressed":u.version===o.version,onClick:()=>{i(u.version),r(0)},children:["v",u.version]},u.version))}),De("span",{className:"faint",style:{marginLeft:"auto",fontSize:12},children:[n.versions.length," version",n.versions.length===1?"":"s"]})]}),De("div",{className:"w-design-body",children:[ie(Hi,{rest:e,stl:o.stl,preview:l,color:null,label:`${n.title} v${o.version}`,className:"short"},`${n.slug}-${o.version}`),De("div",{style:{display:"grid",gap:8,minWidth:0},children:[De("div",{style:{fontWeight:600},children:["v",o.version,o.version===a.version?ie("span",{className:"faint",style:{fontWeight:400},children:", latest"}):null]}),c.length?ie("div",{className:"w-facts-line num",children:c.map(u=>ie("span",{className:u.includes("too big")?"bad":void 0,children:u},u))}):null,o.note?ie("p",{className:"muted",children:o.note}):null,o.previews.length>1?ie("div",{className:"w-strip-thumbs",role:"group","aria-label":"Preview pictures",children:o.previews.map((u,h)=>ie("button",{type:"button","aria-pressed":h===s,"aria-label":`Picture ${h+1}`,onClick:()=>r(h),children:ie(Un,{rest:e,fileRef:u,alt:""})},u))}):null]})]})]})}function kd({ov:n,nowSec:e}){let t=sh(n.setup.checks),i=ih(t),s=rh(n.watcher,e),r=t.filter(c=>c.status!=="ok"),a=t.filter(c=>c.status==="ok"),o=n.watcher.model_calls;return De(Zn,{id:"setup",title:"Health",children:[t.length?De("div",{className:`w-summary t-${i.tone}`,children:[ie(Ie,{name:i.tone==="good"?"check":"alert"}),i.text]}):null,De("div",{className:"w-watch",children:[ie("span",{className:`beat t-${s.tone}`,children:s.text}),o!==null?De("span",{className:`w-zero num${o===0?"":" spent"}`,title:"The watcher checks the printer with plain code: it spends no model calls.",children:[ie("b",{children:o})," model call",o===1?"":"s"]}):null,n.setup.pending?ie("span",{className:"faint","data-workshop-setup":"checking",children:"checking the setup now\u2026"}):Kt(n.setup.checked_ts,e)?De("span",{className:"faint",children:["setup checked ",Kt(n.setup.checked_ts,e)]}):null]}),r.length?ie("ul",{className:"w-rows",children:r.map(c=>De("li",{className:"w-row",style:{alignItems:"flex-start"},children:[ie("span",{className:`lead t-${c.status==="warn"?"warn":"bad"}`,children:ie(Ie,{name:c.status==="warn"?"alert":"x"})}),De("div",{className:"w-main",children:[ie("span",{className:"title",children:c.label}),c.detail?ie("span",{className:"sub",children:c.detail}):null,c.fix?De("span",{className:"w-fix",children:[ie("b",{children:"Fix:"}),ie(zr,{text:c.fix})]}):null]})]},c.id||c.label))}):null,a.length?De("details",{className:"w-more",children:[De("summary",{children:[a.length," check",a.length===1?"":"s"," fine"]}),ie("ul",{className:"w-rows",children:a.map(c=>De("li",{className:"w-row",style:{padding:"6px 0"},children:[ie("span",{className:"lead t-good",children:ie(Ie,{name:"check"})}),De("div",{className:"w-main",children:[ie("span",{children:c.label}),c.detail?ie("span",{className:"sub",children:c.detail}):null]})]},c.id||c.label))})]}):null,t.length?null:ie(Ln,{icon:"wrench",children:n.setup.pending?"The setup check is running; its results show here in a moment.":"The workshop has not run its setup check yet."})]})}import{Fragment as Hd,jsx as Ge,jsxs as ut}from"react/jsx-runtime";function zd({rest:n,copy:e}){let t=Xi(n),i=hh(1e3),s=i/1e3,{ov:r,error:a,failing:o,loading:c,updatedAt:l}=t,u;if(c)u=Ge(nv,{});else if(r){let h=oh(l,i,o);u=Ge(tv,{ov:r,rest:n,nowSec:s,fresh:h,failing:o,errorText:o?Us(a).text:"",onRefresh:t.refetch})}else{let h=Us(a);u=h.kind==="not_enabled"?Ge(iv,{copy:e}):Ge(sv,{text:h.text,onRetry:t.refetch})}return Ge("div",{className:"h3w-scroll","data-workshop-page":"",children:ut("div",{className:"h3w w-page",children:[Ge(Yi,{}),u]})})}function Vd({ov:n,fresh:e,onRefresh:t}){let i=n?.groups.map(s=>s.name)??[];return ut("header",{className:"w-top",children:[ut("div",{children:[Ge("h1",{className:"w-title",children:"Workshop"}),n?ut("p",{className:"w-sub",children:[n.persona||"The printer"," runs the printer",i.length?` for ${i.length===1?i[0]:`${i.slice(0,-1).join(", ")} and ${i[i.length-1]}`}`:"",". People ask in chat; you approve here."]}):null]}),ut("div",{className:"w-top-right",children:[n?.simulated?ut("span",{className:"w-sim",title:"The simulator backend: nothing here moves real hardware.","data-workshop-simulated":"",children:[Ge(Ie,{name:"cube",size:12})," Simulated printer"]}):null,e?.text?ut("span",{className:`w-fresh${e.stale?" stale":""}`,"aria-live":"polite",children:[Ge("span",{className:"w-pulse","aria-hidden":!0}),e.text]}):null,t?Ge("button",{type:"button",className:"w-btn ghost sm",onClick:t,"aria-label":"Refresh now",title:"Refresh now",children:Ge(Ie,{name:"refresh",size:13})}):null]})]})}function tv({ov:n,rest:e,nowSec:t,fresh:i,failing:s,errorText:r,onRefresh:a}){let o={ov:n,rest:e,nowSec:t};return ut(Hd,{children:[Ge(Vd,{ov:n,fresh:i,onRefresh:a}),s?ut("div",{className:"w-banner t-warn",role:"status",children:[Ge(Ie,{name:"alert"}),ut("span",{children:[Ge("b",{children:"The workshop backend stopped answering."})," ",ut("span",{className:"muted",children:["Below is its last answer",i.ago?`, from ${i.ago}`:"",".",r?` (${r})`:""]})]})]}):null,n.viewer.is_owner?null:ut("div",{className:"w-banner t-warn",children:[Ge(Ie,{name:"hand"}),ut("span",{children:[Ge("b",{children:"You are not the printer owner here."})," ",Ge("span",{className:"muted",children:n.viewer.reason||"You can look, but the printer refuses actions from this account."})]})]}),Ge(Cd,{ov:n,rest:e,nowSec:t}),ut("div",{className:"w-grid",children:[ut("div",{className:"w-col",children:[Ge(Nd,{...o}),Ge(Dd,{...o}),Ge(Fd,{...o}),Ge(Od,{...o})]}),ut("div",{className:"w-col",children:[Ge(Ud,{...o}),Ge(Ld,{...o}),Ge(kd,{...o})]})]})]})}function nv(){return ut(Hd,{children:[Ge(Vd,{ov:null}),Ge("div",{className:"w-hero","aria-busy":"true","aria-label":"Loading the workshop",children:ut("div",{className:"w-hero-body",children:[Ge("div",{className:"w-skel",style:{aspectRatio:"4 / 3"}}),ut("div",{style:{display:"grid",gap:12,alignContent:"start"},children:[Ge("div",{className:"w-skel",style:{height:14,width:"30%"}}),Ge("div",{className:"w-skel",style:{height:26,width:"70%"}}),Ge("div",{className:"w-skel",style:{height:90}}),Ge("div",{className:"w-skel",style:{height:40,width:"40%"}})]})]})})]})}var Bd="hermes plugins enable home-3d-workshop";function iv({copy:n}){let[e,t]=ev(!1);return ut("div",{className:"w-state-page","data-workshop-state-page":"not-enabled",children:[ut("h2",{children:[Ge(Ie,{name:"wrench",size:18})," The workshop backend is off"]}),Ge("p",{className:"muted",children:"This screen is on, but the plugin's Python half is not loaded in Hermes, so there is nothing to show yet. It runs the printer, the queue and the approvals."}),ut("ol",{children:[ut("li",{children:["Enable the plugin:",ut("div",{className:"w-code",style:{marginTop:6},children:[Ge("code",{children:Bd}),n?ut("button",{type:"button",className:"w-btn ghost sm",onClick:()=>{n(Bd).then(i=>t(i))},"aria-label":"Copy the command",children:[Ge(Ie,{name:e?"check":"copy",size:12})," ",e?"Copied":"Copy"]}):null]})]}),Ge("li",{children:"Restart Hermes so the backend loads the plugin's routes."}),Ge("li",{children:"Come back here: the page checks again every few seconds."})]})]})}function sv({text:n,onRetry:e}){return ut("div",{className:"w-state-page","data-workshop-state-page":"unreachable",children:[ut("h2",{children:[Ge(Ie,{name:"alert",size:18})," Can't reach the workshop"]}),Ge("p",{className:"muted",children:"The Hermes backend did not answer for the workshop. It may be restarting."}),Ge("div",{className:"w-code",children:Ge("code",{children:n})}),Ge("div",{children:ut("button",{type:"button",className:"w-btn",onClick:e,children:[Ge(Ie,{name:"refresh",size:12})," Try again"]})})]})}import{jsx as Dc}from"react/jsx-runtime";var Gd="home-3d-workshop",Ir="/workshop",hv=["home3d_design"],uv={id:Gd,name:"Workshop",description:"The 3D printer\u2019s back room: what is printing and for whom, approvals with the part in 3D, queue, done box, filament and health.",register(n){let e=n.rest,t=n.os?.writeClipboard?r=>n.os.writeClipboard(r):void 0,i=[{id:"page",area:ov,data:{path:Ir},render:()=>Dc(zd,{rest:e,copy:t})},{id:"nav",area:lv,data:{path:Ir,label:"Workshop",codicon:"tools"}},{id:"chip",area:cv.right,order:90,render:()=>Dc(xh,{rest:e,path:Ir})},{id:"open",area:av,data:{id:`${Gd}.open`,label:"Workshop: open the printer room",keywords:["3d","printer","workshop","print","approve","queue","filament","bambu"],run:()=>{Fs(),rv.navigate(Ir)}}}],s=Wd.TOOL_MEDIA_RENDERER_AREA;typeof s=="string"&&i.push({id:"design-card",area:s,data:{tools:hv,render:r=>Dc(Ed,{props:r,rest:e,path:Ir})}}),n.registerMany(i),n.onEvent("tool.complete",r=>{let a=r.payload?.name;typeof a=="string"&&a.startsWith("home3d_")&&Fs()})}},$M=uv;export{hv as DESIGN_TOOLS,Ir as PATH,Gd as PLUGIN_ID,$M as default};
