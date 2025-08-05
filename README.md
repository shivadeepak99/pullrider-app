# 🛠️ PullRider User Manual (v1.0)[BETA]

**Welcome, Developer. Welcome to a smarter workflow.**

PullRider isn't just another bot. It's your new **AI-powered senior teammate**, designed to review your code, triage your issues, and help you focus on what matters most: *building great software.*  
This guide will show you how to unleash its power in your repository.

---

## 1. 🚀 Installation & Setup: Hiring Your AI Teammate

Getting started is simple and takes less than 60 seconds.

### ✅ Install the App

From the [PullRider Marketplace Page](#), click **"Install"**.

### 📁 Choose Repositories

You have full control. Install PullRider on **all your repositories** or select **specific ones** where you want its help.

### 🔐 Complete the Setup

After installation, you'll be redirected to our secure setup page. Here, you must provide a **Google Gemini API key** to power the AI reviews. You have two options:

- **Easy Setup (Recommended):** Paste your Gemini API key directly into the form. It will be securely stored and associated with your installation.

- **Manual Setup (Advanced):** For maximum control, manage the secret yourself within GitHub.  
  Follow the on-screen instructions to create a repository secret named:

  `PULLRIDER_GEMINI_KEY`

Once setup is complete, PullRider is **on your team**, silently watching and ready to help.

---

## 2. ⚙️ Core Features: What PullRider Does

Once installed and configured, PullRider automatically springs into action.

### 🧠 On Pull Requests: The AI Sensei

When you open a new Pull Request, PullRider performs a full review, just like a senior developer would. It will post a single, helpful comment that:

- ✅ Summarizes the changes in plain English.
- 👁️ Understands the **full context** of changed files (not just the diff).
- 🐛 Points out potential bugs or logic errors.
- 💡 Suggests improvements based on best practices or **your own custom rules** (see below).

### 🕵️ On Issues: The Triage Officer

When a new issue is created, PullRider acts as your team's intelligent gatekeeper:

- 🧐 **Analyzes Issue Quality:**  
  If an issue is vague (e.g., "it broke"), it will politely coach the user on how to write a better bug report.

- 🧹 **Handles Social Chatter:**  
  If someone just says "hello" or drops a casual comment, PullRider replies with wit and auto-closes the issue to keep your tracker clean.

---

## 3. 🧘 Advanced Usage: The Legendary Etiquette

PullRider is designed to feel like a **real teammate**, not a noisy robot.

- 🤫 **Respects Your Workflow:**  
  If a pull request is opened as a **Draft**, PullRider will patiently wait. It leaves a friendly note saying it’ll review once it’s “Ready for Review”.

- 🚫 **Avoids Spam:**  
  It only comments once when a PR or issue is opened. No interruptions, no chaos.

- 🧙‍♂️ **Can Be Summoned:**  
  Need a second look? Just tag the bot in a comment:

  `@pullrider I've updated the code based on your suggestions. Can you take another look?`

  PullRider will re-review the latest code, remembering its past advice like a wise sensei.

---

## 4. 📜 The Scroll of Laws: Customizing Your Sensei

This is PullRider's most powerful feature. You can teach it your team’s specific coding standards.

1. In your repository, create a folder:

   `.github`

2. Inside that folder, create a file named:

   `pullrider.yml`

3. Add your custom rules. For example:

   ```yaml
   # .github/pullrider.yml

   rules:
     - "All Python functions must have a type-hinted return value."
     - "Avoid using console.log() in JavaScript files; use our custom `logger.info()` instead."
     - "All CSS class names must use the BEM naming convention."
   ```
