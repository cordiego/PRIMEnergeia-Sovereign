// PRIMEnergeia — Repo Site JS
function showSection(id){document.querySelectorAll('.page-section').forEach(s=>s.style.display='none');const t=document.getElementById(id);if(t)t.style.display='block';window.scrollTo({top:0,behavior:'smooth'})}
function toggleMobile(){document.getElementById('navLinks').classList.toggle('open')}
window.addEventListener('scroll',()=>{const n=document.getElementById('navbar');if(window.scrollY>50){n.style.background='rgba(5,8,16,0.95)';n.style.borderBottomColor='rgba(26,39,68,0.8)'}else{n.style.background='rgba(5,8,16,0.85)';n.style.borderBottomColor='rgba(26,39,68,0.5)'}});
function createParticles(){const c=document.getElementById('particles');if(!c)return;const n=window.innerWidth<768?25:50;for(let i=0;i<n;i++){const p=document.createElement('div');p.className='particle';p.style.left=Math.random()*100+'%';p.style.animationDuration=(8+Math.random()*12)+'s';p.style.animationDelay=(Math.random()*10)+'s';p.style.width=(1+Math.random()*2)+'px';p.style.height=p.style.width;if(Math.random()>0.7)p.style.background='#00ff88';c.appendChild(p)}}
document.addEventListener('DOMContentLoaded',()=>{createParticles()});
