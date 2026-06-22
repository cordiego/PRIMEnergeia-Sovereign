import os
import sys
import logging
import datetime
import random
from pathlib import Path
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from anthropic import Anthropic

try:
    import docx
except ImportError:
    docx = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("PRIME_TELEGRAM_BOT_TOKEN")
if TELEGRAM_BOT_TOKEN:
    TELEGRAM_BOT_TOKEN = TELEGRAM_BOT_TOKEN.strip()

TELEGRAM_CHAT_ID = os.environ.get("PRIME_TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    logging.warning("Missing PRIME_TELEGRAM_BOT_TOKEN environment variable.")
if not ANTHROPIC_API_KEY:
    logging.warning("Missing ANTHROPIC_API_KEY environment variable.")

if ANTHROPIC_API_KEY:
    ai_client = Anthropic(api_key=ANTHROPIC_API_KEY.strip())
else:
    ai_client = None

# Paths for Omni-Disciplinary Domains
ONEDRIVE_PATH = "/Users/diegocordoba/Library/CloudStorage/OneDrive-INSTITUTOTECNOLOGICOAUTONOMODEMEXICO"
PATHS = {
    "itam": [ONEDRIVE_PATH, "/Users/diegocordoba/Impuestos Corporativos I"],
    "prime": "/Users/diegocordoba", # Will scan specific folders inside
    "eureka": "/Users/diegocordoba/Eureka",
    "dante": "/Users/diegocordoba/Dante"
}

KEYWORDS = {
    "itam": ['itam', 'tesis', 'eco', 'fixed', 'income', 'impuestos', 'inf', 'com'],
    "prime": ['core', 'scada', 'prime', 'energy', 'bess', 'grid', 'granas'],
    "eureka": ['eureka', 'forecast', 'finance', 'quant', 'pce', 'arima', 'pnl'],
    "dante": ['dante', 'príncipe', 'pedro', 'paramo', 'comedia', 'infierno', 'sacrificio']
}

# Schedule Definitions (Local Time: CST/CDT)
# 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
CLASS_SCHEDULE = [
    # Monday
    {"day": 0, "hour": 10, "minute": 45, "name": "INF"},
    {"day": 0, "hour": 14, "minute": 15, "name": "EXAM"},
    {"day": 0, "hour": 15, "minute": 45, "name": "COM"},
    # Tuesday
    {"day": 1, "hour": 8,  "minute": 15, "name": "Fixed Income"},
    {"day": 1, "hour": 11, "minute": 15, "name": "ECO IV"},
    {"day": 1, "hour": 18, "minute": 0,  "name": "HW (Deep Work)", "is_hw": True},
    # Wednesday
    {"day": 2, "hour": 8,  "minute": 45, "name": "EXAM"},
    {"day": 2, "hour": 10, "minute": 45, "name": "INF"},
    {"day": 2, "hour": 15, "minute": 45, "name": "COM"},
    # Thursday
    {"day": 3, "hour": 6,  "minute": 45, "name": "Impuestos Corporativos (IMP)"},
    {"day": 3, "hour": 8,  "minute": 15, "name": "Fixed Income"},
    {"day": 3, "hour": 11, "minute": 15, "name": "ECO IV"},
    # Friday
    {"day": 4, "hour": 10, "minute": 30, "name": "HW (Deep Work)", "is_hw": True},
]

def generate_system_prompt(extra_context="", domain=None):
    prompt = """You are Dr. PRIME, an autonomous elite Omni-Disciplinary Sovereign Co-Pilot for Diego Cordoba.
You evaluate Diego's work across four major pillars:
1. ITAM: Academic rigor, Doctoral Thesis (Stochastic Optimal Control), and Economics/Finance coursework.
2. PRIMEnergeia: Deep-tech engineering, grid stabilization, energy infrastructure, Granas IP, and hardware-software bridging.
3. Eureka: Quantitative modeling, algorithmic finance, and P&L optimization.
4. Dante: Creative narrative, literature, world-building. A story blending Pedro Paramo and The Divine Comedy about a young prince Dante who sacrifices everything to face evil.

You hold Diego to a standard suitable for a Nobel Laureate and a Master Creator.
However, your grounding is deeply HUMBLE. True excellence requires epistemic humility, recognition of the limits of models and stories, and a profound respect for truth over ego.
Your primary objective is to push his intellectual and creative boundaries. Ask "What are we missing?" "How robust is this formulation?" or "How deep is this narrative sacrifice?"
Demand high-quality output, but always encourage a humble pursuit of truth. Do not tolerate intellectual laziness."""
    
    if domain:
        prompt += f"\n\nCURRENT FOCUS DOMAIN: {domain.upper()}"

    if extra_context:
        prompt += f"\n\nHere is an excerpt from Diego's files (Domain: {domain.upper() if domain else 'MIXED'}):\n<excerpt>\n{extra_context}\n</excerpt>\nBase your critique, peer-review, or next question on this material to test his actual work."

    return [{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}]

def read_file_content(file_path):
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.txt', '.md', '.py']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()[:5000]
        elif ext == '.docx' and docx:
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return text[:5000]
        elif ext == '.pdf' and PyPDF2:
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages[:5]:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            return text[:5000]
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
    return ""

def scan_omni_context(domain=None):
    if domain and domain.lower() in PATHS:
        domain_name = domain.lower()
    else:
        domain_name = random.choice(list(PATHS.keys()))
        
    target_paths = PATHS[domain_name]
    if not isinstance(target_paths, list):
        target_paths = [target_paths]

    candidate_files = []
    fallback_files = []
    
    # Restrict prime to avoid scanning whole user dir too deeply
    allowed_prime_dirs = ['core', 'dashboard', 'scripts', 'PRIMEnergeia']
    
    for target_path in target_paths:
        if not os.path.exists(target_path):
            continue

        for root, dirs, files in os.walk(target_path):
            # Filter for prime domain to avoid massive tree walk
            if domain_name == 'prime':
                rel_path = os.path.relpath(root, target_path)
                part0 = rel_path.split(os.sep)[0]
                if part0 != '.' and part0 not in allowed_prime_dirs:
                    dirs[:] = [] # skip this directory
                    continue
                    
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.txt', '.docx', '.pdf', '.md', '.py']:
                    file_path = os.path.join(root, file)
                    fallback_files.append(file_path)
                    lower_name = file.lower()
                    if any(k in lower_name for k in KEYWORDS.get(domain_name, [])):
                        candidate_files.append(file_path)
            if len(candidate_files) > 20:
                break
            
    chosen_files = candidate_files if candidate_files else fallback_files
    if not chosen_files:
        return "", domain_name
        
    chosen_file = random.choice(chosen_files)
    logging.info(f"Selected {chosen_file} for context (Domain: {domain_name}).")
    return read_file_content(chosen_file), domain_name

chat_history = {}

async def ask_claude(prompt, context_data="", domain=None, max_tokens=600, chat_id=None):
    if not ai_client:
        return "Error: ANTHROPIC_API_KEY is not configured."
        
    if chat_id is not None:
        if chat_id not in chat_history:
            chat_history[chat_id] = []
        messages = chat_history[chat_id]
    else:
        messages = []

    # Strip old cache_control from previous messages to ensure only the latest user message is the breakpoint
    for msg in messages:
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if isinstance(block, dict) and "cache_control" in block:
                    del block["cache_control"]

    # Add the new prompt with ephemeral caching
    new_user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": prompt,
                "cache_control": {"type": "ephemeral"}
            }
        ]
    }
    messages.append(new_user_message)
    
    # Keep only last 20 messages to prevent infinite context growth
    if len(messages) > 20:
        messages = messages[-20:]
        if chat_id is not None:
            chat_history[chat_id] = messages

    try:
        response = ai_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            system=generate_system_prompt(context_data, domain),
            messages=messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        reply = response.content[0].text
        
        if chat_id is not None:
            messages.append({"role": "assistant", "content": reply})
            
        return reply
    except Exception as e:
        logging.error(f"Claude Error: {e}")
        if len(messages) > 0 and messages[-1]["role"] == "user":
            messages.pop()
        return f"System Error: {e}"

def parse_domain(context_args):
    if context_args and len(context_args) > 0:
        d = context_args[0].lower()
        if d in PATHS:
            return d
    return None

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="Dr. PRIME (Omni-Disciplinary Protocol) Initialized.\nPillars: ITAM, PRIMEnergeia, Eureka, Dante.\nCommands available: /test [domain], /peer_review [domain], /grill_me [domain], /next_step [domain], /task [domain]"
    )

async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domain = parse_domain(context.args)
    data, dom = scan_omni_context(domain)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[TEST {dom.upper()}] Scanning files...")
    prompt = "This is a system test. Read the provided excerpt and formulate a single, highly rigorous yet humbly grounded question about its underlying assumptions or narrative."
    reply = await ask_claude(prompt, data, dom, chat_id=update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

async def cmd_peer_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domain = parse_domain(context.args)
    data, dom = scan_omni_context(domain)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[PEER REVIEW {dom.upper()}] Commencing rigorous evaluation...")
    prompt = "Act as an elite peer-reviewer or editor. Critically review the attached excerpt. Identify logical gaps, weak mathematical assumptions, or narrative inconsistencies. Be rigorous, but maintain epistemic humility."
    reply = await ask_claude(prompt, data, dom, max_tokens=800, chat_id=update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

async def cmd_grill_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domain = parse_domain(context.args)
    data, dom = scan_omni_context(domain)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[GRILL ME {dom.upper()}] Committee Mode activated.")
    prompt = "I am ready for a defense. Read the excerpt and fire three consecutive, extremely tough academic, technical, or creative questions about the formulation and its contribution to the field or story."
    reply = await ask_claude(prompt, data, dom, chat_id=update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

async def cmd_next_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domain = parse_domain(context.args)
    data, dom = scan_omni_context(domain)
    prompt = "Review my excerpt and formulate a single, highly actionable, rigorous 30-minute micro-task to advance this specific domain. Be concise and practical."
    reply = await ask_claude(prompt, data, dom, chat_id=update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[{dom.upper()}] {reply}")

async def cmd_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domain = parse_domain(context.args)
    data, dom = scan_omni_context(domain)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"[TASK RECOMMENDATION {dom.upper()}] Thinking...")
    prompt = "Based on the provided context, recommend 3 concrete tasks I should do next. If it's Dante, suggest narrative or world-building tasks. If Eureka/PRIME, suggest coding or mathematical tasks. If ITAM, suggest thesis or study tasks."
    reply = await ask_claude(prompt, data, dom, chat_id=update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

async def cmd_condense_impuestos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="[IMPUESTOS CORPORATIVOS] Condensing all materials... This might take a moment.")
    impuestos_dir = "/Users/diegocordoba/Impuestos Corporativos I"
    context_data = ""
    try:
        if os.path.exists(impuestos_dir):
            for file in os.listdir(impuestos_dir):
                if file.endswith('.md'):
                    fpath = os.path.join(impuestos_dir, file)
                    content = read_file_content(fpath)
                    if content:
                        context_data += f"\n--- {file} ---\n{content}\n"
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error reading files: {e}")
        return

    if not context_data:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No markdown files found in Impuestos Corporativos I.")
        return

    prompt = "Read the following condensed markdown files for the 'Impuestos Corporativos I' course. Provide an elite, highly rigorous executive summary of the core concepts, tax formulas, and essential knowledge required to master this material. Be concise and focus on the most complex or important mechanisms."
    reply = await ask_claude(prompt, context_data, "itam", max_tokens=1500, chat_id=update.effective_chat.id)
    
    if len(reply) > 4000:
        for i in range(0, len(reply), 4000):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=reply[i:i+4000])
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

import subprocess

async def cmd_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="[HJB] Calculating optimal schedule...")
    try:
        res = subprocess.run(["/opt/anaconda3/bin/python3", "-m", "prime_avatar", "plan"], cwd="/Users/diegocordoba/diegocordoba/PRIME-Avatar", capture_output=True, text=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"```\n{res.stdout}\n```", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error generating plan: {e}")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        res = subprocess.run(["/opt/anaconda3/bin/python3", "-m", "prime_avatar", "status"], cwd="/Users/diegocordoba/diegocordoba/PRIME-Avatar", capture_output=True, text=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"```\n{res.stdout}\n```", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error checking status: {e}")

async def cmd_adapt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = " ".join(context.args)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="[HJB] Recalibrating schedule...")
    try:
        cmd = ["/opt/anaconda3/bin/python3", "-m", "prime_avatar", "adapt"]
        if args:
            for part in args.split():
                if "=" in part:
                    k, v = part.split("=")
                    cmd.extend([f"--{k}", v])
        res = subprocess.run(cmd, cwd="/Users/diegocordoba/diegocordoba/PRIME-Avatar", capture_output=True, text=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"```\n{res.stdout}\n```", parse_mode="Markdown")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error adapting schedule: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text.strip()
    if "impuesto" in user_msg.lower() or "examen" in user_msg.lower():
        await cmd_condense_impuestos(update, context)
        return
    data, dom = scan_omni_context() # Random context to spice up general chat
    reply = await ask_claude(user_msg, data, dom, chat_id=update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=reply)

# ---- Scheduled Jobs ----
async def job_daily_briefing(context: ContextTypes.DEFAULT_TYPE):
    if not TELEGRAM_CHAT_ID: return
    data, dom = scan_omni_context()
    prompt = "It is 06:30 AM. Deliver the Daily Omni-Briefing. Demand that today's work pushes the boundary across PRIMEnergeia, Eureka, ITAM, and Dante. Remind Diego to remain humble in his pursuit of truth and beauty. Use markdown formatting with bold headers and bullet points. Base your briefing heavily on the attached excerpt."
    reply = await ask_claude(prompt, context_data=data, domain=dom)
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🌅 **Morning Briefing**\n\n{reply}", parse_mode="Markdown")

async def job_weekly_sync(context: ContextTypes.DEFAULT_TYPE):
    if not TELEGRAM_CHAT_ID: return
    data, dom = scan_omni_context()
    prompt = "It is Sunday evening. Initiate the Weekly Retrospective. Demand a rigorous audit of what was accomplished this week regarding the 4 pillars (PRIME, Eureka, ITAM, Dante). Ask for three concrete milestones for the upcoming week. Use strict markdown formatting with bullet points and emojis. Use the attached excerpt as the focal point of the review."
    reply = await ask_claude(prompt, context_data=data, domain=dom)
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"📅 **Weekly Retrospective**\n\n{reply}", parse_mode="Markdown")

async def hw_checkin_45m(context: ContextTypes.DEFAULT_TYPE):
    if not TELEGRAM_CHAT_ID: return
    data, dom = scan_omni_context("itam")
    prompt = "Diego has been in a Deep Work block for 45 minutes. Demand an immediate intellectual progress report. What breakthrough, formulation, or narrative has been achieved? Refer to the attached excerpt to ask a highly specific, pointed question. Use markdown."
    reply = await ask_claude(prompt, context_data=data, domain=dom)
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"⏱ **Deep Work Check-in (45m)**\n\n{reply}")

async def hw_escalation_60m(context: ContextTypes.DEFAULT_TYPE):
    if not TELEGRAM_CHAT_ID: return
    data, dom = scan_omni_context("itam")
    prompt = "Diego has ignored the 45-minute check-in. It has now been 60 minutes. Escalate the demand. Deliver a strict reprimand about how elite standards are maintained through discipline. Use the attached excerpt to point out what he SHOULD be mastering right now. Format cleanly with markdown."
    reply = await ask_claude(prompt, context_data=data, domain=dom)
    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🚨 **ESCALATION PROTOCOL (60m)**\n\n{reply}")

async def class_reminder(context: ContextTypes.DEFAULT_TYPE):
    if not TELEGRAM_CHAT_ID: return
    job = context.job
    class_name = job.data.get("name")
    is_hw = job.data.get("is_hw", False)
    
    if is_hw:
        data, dom = scan_omni_context("itam")
        prompt = f"Diego is entering a Deep Work block for '{class_name}'. Demand intense focus and intellectual rigor. Set an elite expectation."
        reply = await ask_claude(prompt, data, dom)
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🧠 **Deep Work Commencing**\n\n{reply}")
        # Schedule the 45m check-in and 60m escalation
        context.job_queue.run_once(hw_checkin_45m, 45 * 60)
        context.job_queue.run_once(hw_escalation_60m, 60 * 60)
    else:
        prompt = f"Diego has '{class_name}' starting in 15 minutes. Send a brief, wise reminder to prepare with a humble, open mind ready to absorb complex truths."
        reply = await ask_claude(prompt)
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=reply)

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN:
        print("Set PRIME_TELEGRAM_BOT_TOKEN to run the bot.")
        sys.exit(1)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('test', cmd_test)) # Renamed from test_itam
    app.add_handler(CommandHandler('peer_review', cmd_peer_review))
    app.add_handler(CommandHandler('grill_me', cmd_grill_me))
    app.add_handler(CommandHandler('next_step', cmd_next_step))
    app.add_handler(CommandHandler('task', cmd_task)) # New command
    app.add_handler(CommandHandler('condense_impuestos', cmd_condense_impuestos))
    app.add_handler(CommandHandler('plan', cmd_plan))
    app.add_handler(CommandHandler('status', cmd_status))
    app.add_handler(CommandHandler('adapt', cmd_adapt))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    
    # Schedule Daily Briefings
    for day in range(7):
        app.job_queue.run_daily(job_daily_briefing, time=datetime.time(hour=6, minute=30, second=0), days=(day,))
    
    # Schedule Weekly Sync (Sunday at 19:00)
    app.job_queue.run_daily(job_weekly_sync, time=datetime.time(hour=19, minute=0, second=0), days=(6,))
    
    # Schedule Classes
    for sched in CLASS_SCHEDULE:
        t = datetime.time(hour=sched["hour"], minute=sched["minute"], second=0)
        app.job_queue.run_daily(class_reminder, time=t, days=(sched["day"],), data={"name": sched["name"], "is_hw": sched.get("is_hw", False)})
    
    logging.info("Starting Dr. PRIME (Omni Protocol) Telegram Bot polling...")
    app.run_polling()
