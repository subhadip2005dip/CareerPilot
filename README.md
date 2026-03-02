# 🚀 CareerPilot

**CareerPilot** is an end-to-end **AI-driven career optimization platform** built to eliminate blind job applications and equip users with *data-backed, actionable career insights*. It analyzes resumes, identifies skill gaps, simulates interviews, evaluates market demand, and helps users become job-ready with precision.

---

## 🌟 Key Features

✅ **AI Resume Analyzer (Dual Mode)**
- **Candidate Mode**: Semantic matching against job descriptions, ATS scoring, skill extraction, and personalized learning roadmaps
- **Recruiter Mode**: Hiring verdicts, candidate summaries, red flags, interview questions, and salary band recommendations

✅ **Skill Gap Identifier**
- Automatically highlights missing critical skills, nice-to-have skills, and bonus opportunities
- Suggests priority-based learning paths with time estimates

✅ **Mock Interview Simulator**
- Real-time AI-powered interview practice
- Performance evaluation with feedback
- Question and response analysis

✅ **Market Demand Evaluator**
- Analytics on job market trends
- Skill demand across regions and industries
- Competitive positioning insights

✅ **Personalized Learning Roadmaps**
- Day-by-day study plans with milestones
- Curated YouTube resources at beginner/intermediate/expert levels
- Time estimates based on current skill level

✅ **Visual Dashboards & Real-time Metrics**
- Progress tracking for resume improvements
- Interview performance metrics
- Skill match visualizations
- Market insights

✅ **Multi-factor Authentication**
- OAuth 2.0 (Google, LinkedIn, GitHub, Microsoft Entra ID)
- Email/password authentication with JWT sessions

---

## 🛠️ Tech Stack

| Layer | Technology |
|------|------------|
| **Frontend** | Next.js 14, React, TypeScript, Tailwind CSS, Framer Motion |
| **Backend** | FastAPI (Python), Uvicorn |
| **Database** | PostgreSQL + Prisma ORM |
| **Authentication** | NextAuth.js v5, JWT, OAuth 2.0 |
| **AI/NLP** | Transformers, Semantic embeddings, Keyword extraction |
| **UI Components** | Shadcn/ui (headless component library) |
| **Styling** | Tailwind CSS, CSS Modules |
| **Deployment** | Vercel (frontend), Self-hosted/Cloud (backend) |

> This modern stack enables modular design, type safety, and scalable production-grade workflows.

---

## 🧠 How It Works

### Resume Analysis Flow
1. **Resume Upload** → User uploads resume file (PDF/DOCX) via `/upload` page
2. **AI Extraction** → NLP pipeline extracts skills, experience, education, keywords
3. **Job Matching** → Compare against job description using semantic similarity + keyword matching
4. **Dual Analysis**:
   - **Candidate View**: Skill gaps, learning roadmap (phases, milestones, courses)
   - **Recruiter View**: Hiring verdict, calibrated scores, red flags, interview questions

### Interview Simulation
1. **Question Generation** → AI generates role-specific interview questions
2. **Live Chat** → Real-time conversation with AI interviewer
3. **Evaluation** → Automated feedback on content, clarity, technical depth
4. **Report** → Performance metrics and improvement suggestions

### Market Insights
1. **Skill Demand Analysis** → Correlate with job postings
2. **Industry Trends** → Market viability of skills and roles
3. **Salary Expectations** → Regional and role-specific compensation insights

---

## 📦 Installation & Setup

### Prerequisites
- **Node.js** 18+ and npm/yarn
- **Python** 3.10+
- **PostgreSQL** database (local or cloud)
- OAuth API keys (Google, LinkedIn, GitHub, Microsoft Entra ID) — *optional for development*

### 1. Clone the Repository

```bash
git clone https://github.com/SudiptaSaha20/CareerPilot.git
cd CareerPilot
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Create `.env` file in the `backend/` directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/careerpilot
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
# Add other API keys as needed
```

Run migrations (if applicable) and start the server:
```bash
uvicorn api:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd ../frontend
npm install
```

Create `.env.local` file in the `frontend/` directory:
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-random-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/careerpilot

# OAuth Provider Keys (optional for dev)
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret
AZURE_AD_CLIENT_ID=your_id
AZURE_AD_CLIENT_SECRET=your_secret
AZURE_AD_TENANT_ID=your_tenant
LINKEDIN_CLIENT_ID=your_id
LINKEDIN_CLIENT_SECRET=your_secret
GITHUB_CLIENT_ID=your_id
GITHUB_CLIENT_SECRET=your_secret

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the development server:
```bash
npm run dev
```

Visit the application:
```
http://localhost:3000
```

---

## 📌 Usage

### For Job Seekers

1. **Sign Up/Login** → Use email, OAuth, or social login
2. **Upload Resume** → Single upload, reused across all analyses
3. **Analyze & Get Roadmap** → Paste JD → Get skill gaps + learning plan
4. **Practice Interviews** → Simulate role-specific interviews in real-time
5. **Track Progress** → Monitor improvements in dashboard
6. **Explore Market** → Check skill demand and salary insights

### For Recruiters (Recruiter Mode)

1. **Upload Candidate Resume** → Via analysis page
2. **Run Recruiter Analysis** → Get AI-powered hiring verdict
3. **Review Candidate Profile** → Strengths, red flags, culture fit
4. **Get Interview Questions** → AI-suggested questions tailored to gaps
5. **Make Informed Decisions** → Salary band fit, overall match %

---

## 🔌 API Endpoints

### Resume Analysis
- `POST /api/resume/analyze` — Candidate analysis (semantic match, ATS, roadmap)
- `GET /api/resume/latest` — Fetch last analysis (restore state)
- `POST /ats/recruiter` — Recruiter verdict & hiring insights

### Interview
- `POST /api/interview/question` — Generate interview question
- `POST /api/interview/chat` — Real-time chat with AI interviewer
- `POST /api/interview/evaluate` — Get performance feedback

### User & Market
- `GET /api/user/profile` — Fetch user profile
- `POST /api/resume/market/analyze` — Market demand for skills

---

## 🧩 Folder Structure

```
CareerPilot/
├── backend/
│   ├── api.py                      # FastAPI app + endpoints
│   └── requirements.txt             # Python dependencies
│
├── frontend/
│   ├── app/
│   │   ├── api/                    # Next.js API routes
│   │   │   ├── auth/[...nextauth]/ # NextAuth handlers
│   │   │   ├── resume/             # Resume analysis endpoints
│   │   │   └── interview/          # Interview endpoints
│   │   ├── dashboard/              # Main dashboard pages
│   │   ├── upload/                 # Resume upload
│   │   └── profile/                # User profile
│   │
│   ├── components/
│   │   ├── auth/                   # Auth modals & OTP
│   │   ├── ui/                     # Shadcn/ui components
│   │   └── [features]/             # Feature-specific components
│   │
│   ├── context/                    # React Context (resume state)
│   ├── hooks/                      # Custom React hooks
│   ├── lib/                        # Utilities, Prisma client, mailer
│   ├── prisma/                     # Database schema
│   ├── types/                      # TypeScript interfaces
│   │
│   ├── auth.ts                     # NextAuth configuration
│   ├── middleware.ts               # Protected routes
│   ├── next.config.ts              # Next.js config
│   └── tailwind.config.ts          # Styling config
│
├── prisma/
│   └── schema.prisma               # Database schema (ORM)
│
├── LICENSE                         # MIT License
└── README.md                       # This file
```

---

## 🚀 Deployment

### Frontend (Vercel)
```bash
# Push to GitHub, then connect to Vercel
# Set environment variables in Vercel dashboard
npm run build
vercel deploy
```

### Backend (Self-hosted/Cloud)
Deploy to:
- **Railway** / **Render** (Python-friendly, easy setup)
- **AWS EC2** / **DigitalOcean** (VPS with full control)
- **Docker + Container Hub** (Kubernetes, Docker Swarm)

Example Docker deployment:
```bash
docker build -t careerpilot-api .
docker run -p 8000:8000 careerpilot-api
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| OAuth login fails | Check `NEXTAUTH_URL` matches deployment URL; verify OAuth provider credentials |
| Resume upload errors | Ensure file size < 5MB; supported formats: PDF, DOCX |
| Interview chat timeout | Check backend is running; verify `NEXT_PUBLIC_API_URL` is correct |
| Database connection error | Verify PostgreSQL is running; confirm `DATABASE_URL` has correct format |
| Port already in use | Change port: `uvicorn api:app --port 8001` or `npm run dev -- -p 3001` |

---

## 🛠️ Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** and test thoroughly
4. **Commit** with clear messages
   ```bash
   git commit -m "feat: add feature description"
   git commit -m "fix: resolve bug description"
   ```
5. **Push** to your fork and open a **Pull Request**

### Development Guidelines
- Follow existing code style (TypeScript/Python conventions)
- Add tests for new features
- Update README if adding new features
- Keep commits atomic and well-documented

---

## 📊 Current Status

- ✅ Resume analysis with dual modes (candidate/recruiter)
- ✅ AI-powered interview simulator
- ✅ Multi-factor authentication (OAuth + Email)
- ✅ Personalized learning roadmaps with YouTube resources
- ✅ Dashboard with real-time metrics
- ⏳ Market demand analytics (in progress)
- ⏳ LinkedIn/Resume API integrations (planned)
- ⏳ Mobile app (planned)

---

## 🤝 Support & Community

- **Questions?** Open an issue on GitHub
- **Chat with us** → Discussions tab
- **Report bugs** → Issues with reproduction steps
- **Feature requests** → Label as `enhancement`

---

## 📜 License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 📝 Notes for Developers

- CareerPilot uses **Prisma ORM** for type-safe database access
- **NextAuth.js v5** handles authentication (JWT strategy)
- **Shadcn/ui** components ensure consistent, accessible UI
- Backend API is **RESTful** and extensible
- All AI/NLP processing happens server-side for security
- Framer Motion provides smooth animations and transitions

For detailed component documentation, check individual file headers or reach out to maintainers.

---

**Made with ❤️ for career-driven minds.**
