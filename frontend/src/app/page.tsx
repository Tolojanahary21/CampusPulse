"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  GraduationCap,
  Megaphone,
  Menu,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { PreferenceControls, usePreferences } from "@/components/preferences";
import "./landing.css";

export default function Home() {
  const { t } = usePreferences();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const [audience, setAudience] = useState<"students" | "staff">("students");
  const closeMenu = () => setMenuOpen(false);
  const studentAudience = audience === "students";
  const features = [
    {
      icon: Megaphone,
      label: t("S’informer", "Stay informed"),
      title: t("L’essentiel. Au bon moment.", "The essentials. Right on time."),
      body: t(
        "Annonces officielles, événements et actualités : gardez le fil de ce qui compte pour votre établissement et votre parcours.",
        "Official announcements, events and campus news: keep up with what matters to your institution and your studies.",
      ),
      link: t("Retrouver les annonces", "Explore announcements"),
    },
    {
      icon: BookOpen,
      label: t("Apprendre", "Keep learning"),
      title: t("De quoi aller plus loin.", "Everything to take you further."),
      body: t(
        "Cours, exercices, examens et corrigés réunis dans une bibliothèque organisée selon votre formation et vos inscriptions.",
        "Course materials, exercises, exams and answers in a library organised around your programme and enrolments.",
      ),
      link: t("Explorer les ressources", "Explore resources"),
    },
    {
      icon: Users,
      label: t("Se retrouver", "Come together"),
      title: t("Les échanges font grandir.", "Connection helps us grow."),
      body: t(
        "Une question, une idée, une découverte ? Partagez avec les autres étudiants dans un espace communautaire modéré.",
        "A question, an idea, a discovery? Share with fellow students in a moderated community space.",
      ),
      link: t("Rejoindre la communauté", "Join the community"),
    },
  ];
  const audienceItems = studentAudience
    ? [
        t(
          "Les informations qui concernent votre parcours",
          "Updates relevant to your studies",
        ),
        t(
          "Une bibliothèque adaptée à vos inscriptions",
          "A library tailored to your enrolments",
        ),
        t(
          "Un espace pour échanger avec votre communauté",
          "A space to connect with your community",
        ),
      ]
    : [
        t(
          "Des annonces ciblées et des publications planifiées",
          "Targeted announcements and scheduled publishing",
        ),
        t(
          "La gestion des parcours et des ressources pédagogiques",
          "Programme and learning resource management",
        ),
        t(
          "Des permissions et une modération par établissement",
          "Permissions and moderation for each institution",
        ),
      ];

  return (
    <div className="landing-site" id="haut">
      <a className="landing-skip" href="#contenu">
        {t("Aller au contenu", "Skip to content")}
      </a>
      <div className="landing-ribbon">
        <span>
          {t(
            "Apprendre. Partager. Grandir ensemble.",
            "Learn. Share. Grow together.",
          )}
        </span>
        <Link href="/register">
          {t("Rejoindre mon campus", "Join my campus")}{" "}
          <ArrowUpRight size={14} />
        </Link>
      </div>
      <header className="landing-header">
        <Link
          href="/"
          className="landing-brand"
          aria-label={t("CampusPulse, accueil", "CampusPulse, home")}
        >
          <span className="landing-brand-icon">
            <GraduationCap size={25} strokeWidth={1.5} />
          </span>
          <span>
            Campus<strong>Pulse</strong>
            <small>
              {t("LE CAMPUS QUI VOUS RELIE", "YOUR CAMPUS, CONNECTED")}
            </small>
          </span>
        </Link>
        <nav
          className="landing-desktop-nav"
          aria-label={t("Navigation principale", "Main navigation")}
        >
          <a href="#decouvrir">{t("La plateforme", "The platform")}</a>
          <a href="#pour-vous">{t("Pour vous", "For you")}</a>
          <a href="#commencer">{t("Comment ça marche", "How it works")}</a>
        </nav>
        <div className="landing-header-actions">
          <PreferenceControls />
          <Link className="landing-signin" href="/login">
            {t("Mon espace", "My space")} <ArrowUpRight size={15} />
          </Link>
          <button
            className="landing-menu-toggle"
            ref={menuButtonRef}
            type="button"
            aria-label={
              menuOpen
                ? t("Fermer le menu", "Close menu")
                : t("Ouvrir le menu", "Open menu")
            }
            aria-expanded={menuOpen}
            aria-controls="landing-mobile-nav"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </header>
      {menuOpen && (
        <nav
          className="landing-mobile-nav"
          id="landing-mobile-nav"
          aria-label={t("Navigation mobile", "Mobile navigation")}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              closeMenu();
              menuButtonRef.current?.focus();
            }
          }}
        >
          <a href="#decouvrir" onClick={closeMenu}>
            {t("La plateforme", "The platform")} <ArrowRight size={17} />
          </a>
          <a href="#pour-vous" onClick={closeMenu}>
            {t("Pour vous", "For you")} <ArrowRight size={17} />
          </a>
          <a href="#commencer" onClick={closeMenu}>
            {t("Comment ça marche", "How it works")} <ArrowRight size={17} />
          </a>
          <Link href="/register" onClick={closeMenu}>
            {t("Créer mon compte étudiant", "Create my student account")}{" "}
            <ArrowRight size={17} />
          </Link>
          <Link href="/login" onClick={closeMenu}>
            {t("Se connecter", "Sign in")} <ArrowRight size={17} />
          </Link>
        </nav>
      )}
      <main id="contenu">
        <section className="landing-intro" aria-labelledby="landing-title">
          <div className="landing-intro-copy">
            <p className="landing-eyebrow">
              <span />
              {t("VOTRE MONDE UNIVERSITAIRE", "YOUR UNIVERSITY WORLD")}
            </p>
            <h1 id="landing-title">
              {t("Un campus.", "One campus.")}
              <br />
              {t("Des liens.", "Connections.")}
              <br />
              <em>{t("Un avenir.", "A shared future.")}</em>
            </h1>
            <p className="landing-intro-description">
              {t(
                "Tout ce qui fait vivre votre campus, enfin réuni. Les bonnes informations, les ressources pour avancer et une communauté pour grandir.",
                "Everything that brings your campus to life, together at last. The right information, resources to move forward and a community to grow with.",
              )}
            </p>
            <div className="landing-intro-actions">
              <Link
                className="landing-button landing-button-primary"
                href="/register"
              >
                {t("Créer mon compte étudiant", "Create my student account")}{" "}
                <ArrowUpRight size={19} />
              </Link>
              <a className="landing-text-link" href="#decouvrir">
                {t("Découvrir CampusPulse", "Discover CampusPulse")}{" "}
                <ArrowDown size={16} />
              </a>
            </div>
            <div className="landing-intro-footnote">
              <ShieldCheck size={17} />
              <span>
                {t(
                  "Votre établissement. Votre parcours. Votre espace.",
                  "Your institution. Your journey. Your space.",
                )}
              </span>
            </div>
          </div>
          <div className="landing-intro-photo">
            {/* Local photography avoids third-party requests during page loads. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/campus-courtyard.jpg"
              alt={t(
                "Étudiants dans la cour d’une bibliothèque universitaire en briques, sous un ciel bleu",
                "Students in the courtyard of a brick university library beneath a blue sky",
              )}
              width="1800"
              height="2700"
              fetchPriority="high"
            />
            <div className="landing-photo-caption">
              <span>
                {t("LA VIE DE CAMPUS, ENSEMBLE", "CAMPUS LIFE, TOGETHER")}
              </span>
              <p>
                {t("Le début de", "The start of")}
                <br />
                <em>{t("quelque chose de grand.", "something great.")}</em>
              </p>
              <ArrowUpRight size={25} />
            </div>
            <span className="landing-photo-index">01 / CAMPUSPULSE</span>
          </div>
        </section>
        <div
          className="landing-domain-strip"
          aria-label={t(
            "Les essentiels de votre campus",
            "Your campus essentials",
          )}
        >
          <a href="#decouvrir">
            <span>01</span>
            <Megaphone size={18} />
            {t("Les nouvelles du campus", "News from your campus")}
            <ArrowDown size={14} />
          </a>
          <a href="#decouvrir">
            <span>02</span>
            <BookOpen size={18} />
            {t("Le savoir à partager", "Knowledge to share")}
            <ArrowDown size={14} />
          </a>
          <a href="#pour-vous">
            <span>03</span>
            <Users size={18} />
            {t("Une communauté à retrouver", "A community to connect with")}
            <ArrowDown size={14} />
          </a>
        </div>
        <section
          className="landing-platform landing-section"
          id="decouvrir"
          aria-labelledby="platform-title"
        >
          <div className="landing-section-top">
            <div>
              <p className="landing-eyebrow">
                {t("LE LIEN CAMPUSPULSE", "THE CAMPUSPULSE CONNECTION")}
              </p>
              <h2 id="platform-title">
                {t("Moins chercher.", "Less searching.")}
                <br />
                <em>{t("Plus avancer.", "More moving forward.")}</em>
              </h2>
            </div>
            <p>
              {t(
                "L’université, c’est bien plus que des cours. CampusPulse rapproche les personnes, les connaissances et les opportunités qui font votre quotidien.",
                "University is about more than classes. CampusPulse brings together the people, knowledge and opportunities that shape your everyday life.",
              )}
            </p>
          </div>
          <div className="landing-feature-columns">
            {features.map((feature, index) => (
              <article className="landing-feature-column" key={index}>
                <div className="landing-feature-top">
                  <span className="landing-feature-icon">
                    <feature.icon size={25} strokeWidth={1.4} />
                  </span>
                  <span className="landing-feature-number">0{index + 1}</span>
                </div>
                <p className="landing-feature-label">{feature.label}</p>
                <h3>{feature.title}</h3>
                <p className="landing-feature-body">{feature.body}</p>
                <Link href="/login" className="landing-text-link">
                  {feature.link}
                  <ArrowUpRight size={18} />
                </Link>
              </article>
            ))}
          </div>
        </section>
        <section
          className="landing-audience"
          id="pour-vous"
          aria-labelledby="audience-title"
        >
          <div className="landing-audience-photo">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/images/campus-library.jpg"
              width="1200"
              height="1903"
              loading="lazy"
              alt={t(
                "Des étudiants travaillent dans la grande salle de lecture d’une bibliothèque",
                "Students working in a library’s grand reading room",
              )}
            />
            <div className="landing-library-caption">
              <BookOpen size={22} />
              <span>
                {t("Le savoir se partage.", "Knowledge is meant to be shared.")}
                <br />
                <em>
                  {t(
                    "L’avenir se construit ensemble.",
                    "The future is built together.",
                  )}
                </em>
              </span>
            </div>
          </div>
          <div className="landing-audience-copy">
            <p className="landing-eyebrow">
              {t(
                "CHACUN SA PLACE. UN MÊME CAMPUS.",
                "YOUR OWN PLACE. ONE SHARED CAMPUS.",
              )}
            </p>
            <h2 id="audience-title">
              {t("Pensé pour vous.", "Built around you.")}
              <br />
              <em>
                {t("Fait pour être ensemble.", "Made to bring us together.")}
              </em>
            </h2>
            <div
              className="landing-audience-tabs"
              role="tablist"
              aria-label={t(
                "Découvrir selon votre profil",
                "Explore by your role",
              )}
            >
              {(["students", "staff"] as const).map((item, index) => (
                <button
                  key={item}
                  id={`audience-tab-${item}`}
                  type="button"
                  role="tab"
                  aria-selected={audience === item}
                  aria-controls="audience-panel"
                  tabIndex={audience === item ? 0 : -1}
                  onClick={() => setAudience(item)}
                  onKeyDown={(event) => {
                    if (
                      ["ArrowLeft", "ArrowRight", "Home", "End"].includes(
                        event.key,
                      )
                    ) {
                      event.preventDefault();
                      const next =
                        event.key === "Home"
                          ? "students"
                          : event.key === "End"
                            ? "staff"
                            : item === "students"
                              ? "staff"
                              : "students";
                      setAudience(next);
                      document.getElementById(`audience-tab-${next}`)?.focus();
                    }
                  }}
                >
                  {index === 0
                    ? t("Étudiants", "Students")
                    : t("Équipes du campus", "Campus teams")}
                </button>
              ))}
            </div>
            <div
              id="audience-panel"
              className="landing-audience-panel"
              role="tabpanel"
              aria-labelledby={`audience-tab-${audience}`}
              tabIndex={0}
            >
              <h3>
                {studentAudience
                  ? t(
                      "Votre quotidien, un peu plus simple.",
                      "Your everyday life, a little simpler.",
                    )
                  : t(
                      "Donnez le rythme à votre campus.",
                      "Set the pace for your campus.",
                    )}
              </h3>
              <p>
                {studentAudience
                  ? t(
                      "Retrouvez votre établissement et construisez votre vie étudiante à votre rythme, avec l’essentiel toujours à portée de main.",
                      "Connect with your institution and shape your student life at your own pace, with the essentials always within reach.",
                    )
                  : t(
                      "Reliez votre établissement à ses étudiants avec des espaces de travail adaptés aux responsabilités de chaque équipe.",
                      "Connect your institution with its students through workspaces tailored to each team’s responsibilities.",
                    )}
              </p>
              <ul>
                {audienceItems.map((item) => (
                  <li key={item}>
                    <Check size={17} />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <Link
                className="landing-button landing-button-primary"
                href={studentAudience ? "/register" : "/login"}
              >
                {studentAudience
                  ? t("Rejoindre mon campus", "Join my campus")
                  : t("Accéder à mon espace", "Open my workspace")}
                <ArrowUpRight size={18} />
              </Link>
              {!studentAudience && (
                <p className="landing-role-note">
                  {t(
                    "Les comptes des responsables, de publication et de modération sont créés par l’administration.",
                    "Administrator, publishing and moderation accounts are created by the administration.",
                  )}
                </p>
              )}
            </div>
          </div>
        </section>
        <section
          className="landing-start landing-section"
          id="commencer"
          aria-labelledby="start-title"
        >
          <div className="landing-section-top">
            <div>
              <p className="landing-eyebrow">
                {t("VOTRE PROCHAIN CHAPITRE", "YOUR NEXT CHAPTER")}
              </p>
              <h2 id="start-title">
                {t("Tout commence", "It all starts")}
                <br />
                <em>{t("par une connexion.", "with a connection.")}</em>
              </h2>
            </div>
            <p>
              {t(
                "Vous êtes étudiant ? Créez votre compte et retrouvez l’espace de votre établissement. Quelques étapes pour vous sentir déjà chez vous.",
                "Are you a student? Create your account and find your institution’s space. A few simple steps to feel right at home.",
              )}
            </p>
          </div>
          <ol className="landing-steps">
            <li>
              <span>01</span>
              <h3>{t("Trouvez votre campus", "Find your campus")}</h3>
              <p>
                {t(
                  "Choisissez votre établissement parmi ceux qui accueillent les inscriptions.",
                  "Choose your institution from those accepting registrations.",
                )}
              </p>
            </li>
            <li>
              <span>02</span>
              <h3>{t("Créez votre compte", "Create your account")}</h3>
              <p>
                {t(
                  "Renseignez votre profil étudiant et vos informations de connexion.",
                  "Enter your student details and set up your sign-in information.",
                )}
              </p>
            </li>
            <li>
              <span>03</span>
              <h3>{t("Prenez votre place", "Make yourself at home")}</h3>
              <p>
                {t(
                  "Découvrez les annonces et la communauté. Votre administration valide ensuite votre parcours pour les ressources ciblées.",
                  "Discover announcements and the community. Your administration then confirms your programme to unlock targeted resources.",
                )}
              </p>
            </li>
          </ol>
        </section>
        <section
          className="landing-invitation"
          aria-labelledby="invitation-title"
        >
          <div className="landing-invitation-symbol" aria-hidden="true">
            <GraduationCap size={75} strokeWidth={0.8} />
          </div>
          <div>
            <p className="landing-eyebrow">
              {t("ON SE RETROUVE SUR LE CAMPUS ?", "SEE YOU ON CAMPUS?")}
            </p>
            <h2 id="invitation-title">
              {t("Votre place vous attend.", "Your place is waiting.")}
            </h2>
          </div>
          <Link
            className="landing-button landing-button-light"
            href="/register"
          >
            {t("Créer mon compte étudiant", "Create my student account")}
            <ArrowUpRight size={19} />
          </Link>
        </section>
      </main>
      <footer className="landing-footer">
        <div className="landing-footer-top">
          <Link href="/" className="landing-brand">
            <span className="landing-brand-icon">
              <GraduationCap size={25} strokeWidth={1.5} />
            </span>
            <span>
              Campus<strong>Pulse</strong>
              <small>
                {t("LE CAMPUS QUI VOUS RELIE", "YOUR CAMPUS, CONNECTED")}
              </small>
            </span>
          </Link>
          <p>
            {t("Des personnes. Des connaissances.", "People. Knowledge.")}
            <br />
            {t("Et tout un avenir à partager.", "And a whole future to share.")}
          </p>
          <nav aria-label={t("Liens de bas de page", "Footer links")}>
            <a href="#decouvrir">{t("La plateforme", "The platform")}</a>
            <Link href="/register">
              {t("Inscription étudiante", "Student registration")}
            </Link>
            <Link href="/login">{t("Se connecter", "Sign in")}</Link>
          </nav>
        </div>
        <div className="landing-footer-bottom">
          <span>© {new Date().getFullYear()} Tolojanahary · CampusPulse. Tous droits réservés.</span>
          <span>
            {t("Photographies :", "Photography:")}{" "}
            <a
              href="https://unsplash.com/@zoshuacolah"
              target="_blank"
              rel="noreferrer"
            >
              Zoshua Colah / Unsplash
            </a>
          </span>
          <a href="#haut">
            {t("Retour en haut", "Back to top")} <ArrowUpRight size={15} />
          </a>
        </div>
      </footer>
    </div>
  );
}
