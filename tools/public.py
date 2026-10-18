"""The public, crawlable side of doelenboek.be, written next to index.html by tools/build.py.

The app itself is drawn by JavaScript after login, so search engines and AI assistants (most AI
crawlers do not run JavaScript at all) would otherwise only see an empty page. This module writes
plain HTML pages that say what Doelenboek is and list the built-in minimumdoelen, in Dutch and
English, plus the files crawlers look for:

  over/, en/about/                          what Doelenboek is, how it works, questions and answers
  minimumdoelen/, en/minimum-goals/         the subjects, and one page per subject with its goals
  robots.txt, sitemap.xml                   for search engines
  llms.txt, llms-full.txt                   a summary and the full goal lists in Markdown, for AI assistants
  og-image.png                              the preview picture when a link is shared

The texts are in TEXT below; the look is design/tokens.css plus design/site.css."""
import json, re, shutil
from html import escape
from pathlib import Path

SITE = 'https://doelenboek.be'
NAME = 'Doelenboek'
KOFI = 'https://ko-fi.com/mat644'
SOURCE = 'https://onderwijsdoelen.be'

# paths of the pages, per language, without the leading and trailing slash
ABOUT = {'nl': 'over', 'en': 'en/about'}
GOALS = {'nl': 'minimumdoelen', 'en': 'en/minimum-goals'}
SUBJECT_SLUG_EN = {'NL': 'dutch', 'WK': 'mathematics', 'WT': 'science-and-technology', 'GE': 'history',
                   'AK': 'geography', 'MV': 'arts-education', 'LO': 'physical-education', 'AT': 'attitudes'}

TEXT = {
    'nl': {
        'tagline': 'Huisonderwijs bijhouden en koppelen aan de Vlaamse minimumdoelen',
        'summary': 'Doelenboek is een gratis webapp voor ouders die in Vlaanderen huisonderwijs geven. '
                   'Noteer wat je samen met je kinderen doet, met foto\'s, koppel het aan de minimumdoelen '
                   'en zie per kind en per vak welke doelen al aan bod kwamen en welke nog openstaan.',
        'meta_desc': 'Gratis webapp voor huisonderwijs in Vlaanderen: noteer activiteiten met foto\'s, koppel ze aan de minimumdoelen '
                     'en zie per kind en per vak wat nog openstaat.',
        'goals_desc': lambda subj: f'De Vlaamse minimumdoelen voor het kleuteronderwijs per vak, met code en categorie: {subj}.',
        'nav_about': 'Over Doelenboek', 'nav_goals': 'Minimumdoelen', 'open_app': 'Open de app',
        'other_lang': 'English', 'skip': 'Naar de inhoud',
        'about_title': 'Over Doelenboek: huisonderwijs bijhouden met de minimumdoelen',
        'about_h1': 'Huisonderwijs bijhouden, gekoppeld aan de minimumdoelen',
        'how_h': 'Zo werkt het',
        'how': [
            ('Voeg je kinderen toe', 'Elk kind krijgt een eigen naam en een dierenfiguurtje, zodat je ze op elk scherm meteen herkent.'),
            ('Noteer wat jullie doen', 'Een uitstap naar het bos, een kookmoment, een voorleesboek: schrijf het kort op, kies de datum, de kinderen die meededen en voeg foto\'s toe.'),
            ('Koppel het aan de minimumdoelen', 'Kies bij elke activiteit de minimumdoelen waaraan je werkte. Doelenboek bevat de Vlaamse minimumdoelen, per vak en per categorie, met hun officiële code.'),
            ('Zie wat nog openstaat', 'Per kind en per vak zie je hoeveel doelen al aan bod kwamen, hoe vaak, en welke nog niet. Duid aan wanneer een kind een doel beheerst.'),
        ],
        'features_h': 'Wat je krijgt',
        'features': [
            'Gratis, zonder advertenties en zonder cookies op je toestel',
            'In het Nederlands en het Engels; de doelen staan er in beide talen',
            'Werkt op elke computer, tablet of telefoon, in de browser',
            'Een account met e-mailadres en wachtwoord, zodat je gegevens op al je toestellen staan',
            'Foto\'s bij elke activiteit, verkleind bewaard',
            'Je gegevens staan in Google Firebase in de EU en je kunt ze op elk moment volledig verwijderen',
        ],
        'faq_h': 'Vragen en antwoorden',
        'faq': [
            ('Wat is Doelenboek?',
             'Doelenboek is een gratis webapp voor ouders die in Vlaanderen huisonderwijs geven. Je noteert wat je '
             'met je kinderen doet, koppelt dat aan de Vlaamse minimumdoelen en ziet per kind en per vak welke doelen '
             'al aan bod kwamen en welke nog openstaan.'),
            ('Wat zijn minimumdoelen?',
             'Minimumdoelen zijn de doelen die de Vlaamse overheid vastlegt voor het onderwijs: wat kinderen minstens '
             'moeten kennen en kunnen. De officiële teksten staan op onderwijsdoelen.be. Doelenboek neemt ze over, '
             'per vak en met hun code, zodat je ze bij elke activiteit kunt kiezen.'),
            ('Welke minimumdoelen staan er in Doelenboek?',
             'Op dit moment de minimumdoelen voor het kleuteronderwijs, voor {subjects}. Andere vakken volgen. '
             'Je vindt de volledige lijsten op deze website, onder Minimumdoelen.'),
            ('Kost Doelenboek iets?',
             'Nee. Doelenboek is gratis en toont geen advertenties. Wie het project wil steunen, kan een vrijwillige '
             'donatie doen via Ko-fi; dat helpt de kosten van de hosting te dekken.'),
            ('Waar worden mijn gegevens bewaard?',
             'Je kinderen, activiteiten en foto\'s worden bewaard in Google Firebase in de EU. Ze zijn alleen bereikbaar '
             'met jouw e-mailadres en wachtwoord. De website slaat geen cookies op je toestel op, en je kunt je account '
             'en al je gegevens altijd zelf verwijderen.'),
            ('Moet ik iets installeren?',
             'Nee. Doelenboek werkt in de browser op een computer, tablet of telefoon. Maak een account aan met je '
             'e-mailadres en een wachtwoord, en je gegevens staan op al je toestellen.'),
            ('Is Doelenboek ook in het Engels?',
             'Ja. Je wisselt in de app tussen Nederlands en Engels. De minimumdoelen staan er in het Engels als '
             'vertaling van de officiële Nederlandse tekst.'),
            ('Vervangt Doelenboek de officiële regels voor huisonderwijs?',
             'Nee. Doelenboek helpt je bijhouden wat je kinderen leren, maar het is geen officieel document. Wij zijn '
             'niet verantwoordelijk voor de volledigheid van de minimumdoelen; de officiële lijsten staan op '
             'onderwijsdoelen.be.'),
        ],
        'cta_h': 'Probeer het zelf', 'cta_p': 'Maak gratis een account aan en voeg je eerste kind en activiteit toe.',
        'goals_title': 'Minimumdoelen kleuteronderwijs per vak',
        'goals_h1': 'Minimumdoelen per vak',
        'goals_lede': 'De doelen waartegen je de voortgang meet. Officiële lijsten vind je op',   # as in the app
        'n_goals': lambda n: f'{n} minimumdoel' + ('' if n == 1 else 'en'),
        'coming': 'volgt nog',
        'subject_title': lambda s: f'Minimumdoelen {s.lower() if s != "Nederlands" else s} kleuteronderwijs',
        'subject_h1': lambda s: f'Minimumdoelen {s}',
        'subject_lede': lambda s, n: f'De {n} Vlaamse minimumdoelen voor {s} in het kleuteronderwijs, met hun officiële code, '
                                     f'gegroepeerd per categorie. Met Doelenboek houd je per kind bij welke ervan al aan bod kwamen.',
        'subject_desc': lambda s, n: f'Alle {n} Vlaamse minimumdoelen {s} voor het kleuteronderwijs, met code en categorie. '
                                     f'Houd ze per kind bij in huisonderwijs met Doelenboek.',
        'other_subjects': 'Andere vakken',
        'source': 'Bron: de officiële minimumdoelen op',
        'disclaimer': 'Wij zijn niet verantwoordelijk voor de volledigheid van de minimumdoelen.',
        'foot_cookies': 'Deze website slaat geen cookies op je toestel op.',
        'support': 'Doneren via Ko-fi',
        'subject_word': 'Vak', 'category_word': 'Categorie',
        'app_title': 'Doelenboek: huisonderwijs bijhouden met de Vlaamse minimumdoelen',
        'noscript': 'Doelenboek heeft JavaScript nodig. Lees intussen meer over Doelenboek of bekijk de minimumdoelen per vak.',
    },
    'en': {
        'tagline': 'Keep track of homeschooling against the Flemish minimum goals',
        'summary': 'Doelenboek is a free web app for parents who homeschool in Flanders, Belgium. Note down what you do '
                   'with your children, with photos, link it to the Flemish minimum goals (minimumdoelen) and see per '
                   'child and per subject which goals have been covered and which are still open.',
        'meta_desc': 'Free web app for homeschooling in Flanders: log activities with photos, link them to the Flemish minimum goals '
                     'and see per child and subject what is still open.',
        'goals_desc': lambda subj: f'The Flemish preschool minimum goals (minimumdoelen) by subject, with code and category: {subj}.',
        'nav_about': 'About Doelenboek', 'nav_goals': 'Minimum goals', 'open_app': 'Open the app',
        'other_lang': 'Nederlands', 'skip': 'Skip to content',
        'about_title': 'About Doelenboek: a homeschool tracker for the Flemish minimum goals',
        'about_h1': 'Track homeschooling against the Flemish minimum goals',
        'how_h': 'How it works',
        'how': [
            ('Add your children', 'Each child gets a name and a small animal picture, so you recognise them at a glance on every screen.'),
            ('Note down what you do', 'A walk in the woods, cooking together, a picture book: write it down briefly, pick the date and the children who took part, and add photos.'),
            ('Link it to the minimum goals', 'For each activity, pick the minimum goals you worked on. Doelenboek includes the Flemish minimum goals by subject and category, with their official code.'),
            ('See what is still open', 'Per child and per subject you see how many goals have been covered, how often, and which ones not yet. Mark when a child has mastered a goal.'),
        ],
        'features_h': 'What you get',
        'features': [
            'Free, without ads and without cookies on your device',
            'In Dutch and English; the goals are available in both languages',
            'Works in the browser on any computer, tablet or phone',
            'An account with email and password, so your data is on all your devices',
            'Photos with every activity, stored at a reduced size',
            'Your data is stored in Google Firebase in the EU, and you can delete all of it at any time',
        ],
        'faq_h': 'Questions and answers',
        'faq': [
            ('What is Doelenboek?',
             'Doelenboek is a free web app for parents who homeschool in Flanders, Belgium. You note down what you do '
             'with your children, link it to the Flemish minimum goals and see per child and per subject which goals '
             'have been covered and which are still open.'),
            ('What are the minimum goals (minimumdoelen)?',
             'The minimum goals are the learning goals the Flemish government sets for education: what children should '
             'at least know and be able to do. The official texts are published in Dutch on onderwijsdoelen.be. '
             'Doelenboek includes them by subject, with their code, so you can pick them for every activity.'),
            ('Which minimum goals does Doelenboek include?',
             'At the moment the minimum goals for preschool (kleuteronderwijs), for {subjects}. Other subjects will '
             'follow. The full lists are on this website, under Minimum goals.'),
            ('Does Doelenboek cost anything?',
             'No. Doelenboek is free and shows no ads. If you would like to support the project, you can make a '
             'voluntary donation on Ko-fi, which helps cover the hosting costs.'),
            ('Where is my data stored?',
             'Your children, activities and photos are stored in Google Firebase in the EU and can only be reached with '
             'your email address and password. The website does not store cookies on your device, and you can delete '
             'your account and all your data yourself at any time.'),
            ('Do I need to install anything?',
             'No. Doelenboek works in the browser on a computer, tablet or phone. Create an account with your email '
             'address and a password, and your data is on all your devices.'),
            ('Is Doelenboek available in English?',
             'Yes. You can switch between Dutch and English in the app. The minimum goals are shown in English as a '
             'translation of the official Dutch wording.'),
            ('Does Doelenboek replace the official homeschooling rules?',
             'No. Doelenboek helps you keep track of what your children learn, but it is not an official document. We '
             'do not take responsibility for the completeness of the minimum goals; the official lists are on '
             'onderwijsdoelen.be.'),
        ],
        'cta_h': 'Try it yourself', 'cta_p': 'Create a free account and add your first child and activity.',
        'goals_title': 'Flemish preschool minimum goals by subject',
        'goals_h1': 'Minimum goals by subject',
        'goals_lede': 'The goals to track progress against, translated from the official lists on',   # as in the app
        'n_goals': lambda n: f'{n} minimum goal' + ('' if n == 1 else 's'),
        'coming': 'coming later',
        'subject_title': lambda s: f'Flemish preschool minimum goals for {s.lower() if s != "Dutch" else s}',
        'subject_h1': lambda s: f'Minimum goals: {s}',
        'subject_lede': lambda s, n: f'The {n} Flemish minimum goals for {s.lower() if s != "Dutch" else s} in preschool (kleuteronderwijs), '
                                     f'with their official code, grouped by category. With Doelenboek you track per child which of them have been covered.',
        'subject_desc': lambda s, n: f'All {n} Flemish preschool minimum goals (minimumdoelen) for {s.lower() if s != "Dutch" else s}, '
                                     f'with code and category. Track them per child when homeschooling with Doelenboek.',
        'other_subjects': 'Other subjects',
        'source': 'Source: the official minimum goals (in Dutch) on',
        'disclaimer': 'We do not take responsibility for the completeness of the minimum goals.',
        'foot_cookies': 'This website does not store cookies on your device.',
        'support': 'Donate on Ko-fi',
        'subject_word': 'Subject', 'category_word': 'Category',
        'app_title': 'Doelenboek: homeschool tracker for the Flemish minimum goals',
        'noscript': 'Doelenboek needs JavaScript. Meanwhile, read more about Doelenboek or see the minimum goals by subject.',
    },
}
LOCALE = {'nl': 'nl_BE', 'en': 'en_GB'}


def url(path):
    return f'{SITE}/{path}/' if path else f'{SITE}/'


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def anchor(code):
    return 'doel-' + code.replace('.', '-')


def load_subjects(doelen_dir, subject_keys):
    """The subjects in app order, each with its goals (in file order) grouped by category."""
    by_key = {}
    for path in doelen_dir.glob('*.json'):
        doc = json.loads(path.read_text(encoding='utf-8'))
        by_key[doc['subject']] = {'key': doc['subject'], 'name': {'nl': doc['name'], 'en': doc.get('nameEn') or doc['name']},
                                  'slug': {'nl': path.stem, 'en': SUBJECT_SLUG_EN.get(doc['subject'], slugify(doc.get('nameEn') or path.stem))},
                                  'goals': doc['doelen']}
    return [by_key[k] for k in subject_keys if k in by_key]


def grouped(goals, lang):
    groups = {}
    for g in goals:
        cat = (g.get('categoryEn') if lang == 'en' else None) or g.get('category') or ''
        groups.setdefault(cat, []).append(g)
    return groups


def desc(g, lang):
    return (g.get('descriptionEn') if lang == 'en' else None) or g['description']


def subject_list(subjects, lang):
    # subject names are lower case mid-sentence, except the language itself (Nederlands, Dutch)
    names = [s['name'][lang] if s['key'] == 'NL' else s['name'][lang].lower() for s in subjects if s['goals']]
    joiner = ' en ' if lang == 'nl' else ' and '
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + joiner + names[-1]


def json_ld(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + '</script>'


def breadcrumbs(items):
    return {'@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i, 'name': name, 'item': url(path)} for i, (name, path) in enumerate(items, 1)]}


WEBSITE = {'@type': 'WebSite', '@id': f'{SITE}/#website', 'url': f'{SITE}/', 'name': NAME,
           'alternateName': 'doelenboek.be', 'inLanguage': ['nl-BE', 'en']}


def app_entity(lang, subjects):
    T = TEXT[lang]
    return {
        '@type': 'WebApplication', '@id': f'{SITE}/#app', 'name': NAME, 'url': f'{SITE}/',
        'description': T['summary'], 'applicationCategory': 'EducationalApplication', 'operatingSystem': 'Any (web browser)',
        'browserRequirements': 'Requires JavaScript', 'inLanguage': ['nl-BE', 'en'], 'isAccessibleForFree': True,
        'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'EUR'},
        'image': f'{SITE}/og-image.png', 'featureList': T['features'],
        'audience': {'@type': 'ParentAudience', 'audienceType': 'Parents who homeschool in Flanders, Belgium',
                     'geographicArea': {'@type': 'AdministrativeArea', 'name': 'Vlaanderen (Flanders), Belgium'}},
        'about': [{'@type': 'Thing', 'name': 'Huisonderwijs (homeschooling) in Vlaanderen'},
                  {'@type': 'Thing', 'name': 'Minimumdoelen kleuteronderwijs', 'sameAs': SOURCE}],
        'isPartOf': {'@id': f'{SITE}/#website'},
    }


def head(lang, title, description, path, alternates, extra_ld, css):
    """<head> for a static page. alternates: {lang: path} of the same page in every language."""
    links = ''.join(f'<link rel="alternate" hreflang="{l}" href="{url(p)}">' for l, p in alternates.items())
    links += f'<link rel="alternate" hreflang="x-default" href="{url(alternates["nl"])}">'
    og_alt = ''.join(f'<meta property="og:locale:alternate" content="{LOCALE[l]}">' for l in alternates if l != lang)
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
<link rel="canonical" href="{url(path)}">
{links}
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
{social_meta(lang, title, description, url(path))}{og_alt}
<meta name="theme-color" content="#725C4E">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/fonts/clarity-city-latin.woff2" as="font" type="font/woff2" crossorigin>
<script>let t = 'light'; try {{ if (localStorage.getItem('doelenboek.theme') === 'dark') t = 'dark'; }} catch (e) {{}} document.documentElement.dataset.theme = t;</script>
<style>
{css}
</style>
{json_ld({'@context': 'https://schema.org', '@graph': [WEBSITE] + extra_ld})}
</head>"""


def social_meta(lang, title, description, page_url):
    return f"""<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:locale" content="{LOCALE[lang]}">
<meta property="og:title" content="{escape(title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{page_url}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{escape(TEXT[lang]['tagline'])}">
<meta name="twitter:card" content="summary_large_image">
"""


def page(lang, title, description, path, alternates, extra_ld, css, current, body):
    T = TEXT[lang]
    other = 'en' if lang == 'nl' else 'nl'
    cur = ' aria-current="page"'
    nav = ''.join(f'<a href="/{p}/"{cur if current == k else ""}>{escape(T[label])}</a>'
                  for k, p, label in (('about', ABOUT[lang], 'nav_about'), ('goals', GOALS[lang], 'nav_goals')))
    return f"""{head(lang, title, description, path, alternates, extra_ld, css)}
<body>
<a class="skip" href="#inhoud">{escape(T['skip'])}</a>
<header class="top">
  <div class="top-inner">
    <a class="brand" href="/{ABOUT[lang]}/"><b>doelenboek.be</b></a>
    <nav class="site-nav" aria-label="{NAME}">{nav}</nav>
    <div class="top-right">
      <a class="lang-link" href="/{alternates[other]}/" hreflang="{other}" lang="{other}">{escape(T['other_lang'])}</a>
      <a class="btn small" href="/">{escape(T['open_app'])}</a>
    </div>
  </div>
</header>
<main id="inhoud" class="site-main">
{body}
</main>
<footer class="site-foot">
  <p>{escape(T['foot_cookies'])}</p>
  <p>{escape(T['disclaimer'])}</p>
  <p><a href="/{ABOUT[lang]}/">{escape(T['nav_about'])}</a> · <a href="/{GOALS[lang]}/">{escape(T['nav_goals'])}</a> · <a href="{KOFI}" rel="noopener">{escape(T['support'])}</a></p>
</footer>
</body>
</html>
"""


def about_page(lang, subjects, css):
    T = TEXT[lang]
    subj = subject_list(subjects, lang)
    faq = [(q, a.replace('{subjects}', subj)) for q, a in T['faq']]
    steps = ''.join(f'<li><h3>{escape(h)}</h3><p>{escape(p)}</p></li>' for h, p in T['how'])
    feats = ''.join(f'<li>{escape(f)}</li>' for f in T['features'])
    qa = ''.join(f'<div class="qa"><h3>{escape(q)}</h3><p>{escape(a)}</p></div>' for q, a in faq)
    goals = ''.join(f'<li><a href="/{GOALS[lang]}/{s["slug"][lang]}/">{escape(s["name"][lang])}</a> <span class="muted">· {escape(T["n_goals"](len(s["goals"])))}</span></li>'
                    for s in subjects if s['goals'])
    body = f"""<article class="prose">
<header class="hero card">
  <h1>{escape(T['about_h1'])}</h1>
  <p class="lede">{escape(T['summary'])}</p>
  <p><a class="btn primary" href="/">{escape(T['open_app'])}</a></p>
</header>
<section aria-labelledby="hoe"><h2 id="hoe">{escape(T['how_h'])}</h2><ol class="steps">{steps}</ol></section>
<section aria-labelledby="wat"><h2 id="wat">{escape(T['features_h'])}</h2><ul class="ticks">{feats}</ul></section>
<section aria-labelledby="doelen"><h2 id="doelen">{escape(T['nav_goals'])}</h2><ul>{goals}</ul></section>
<section aria-labelledby="faq"><h2 id="faq">{escape(T['faq_h'])}</h2>{qa}</section>
<section class="card cta"><h2>{escape(T['cta_h'])}</h2><p>{escape(T['cta_p'])}</p><p><a class="btn primary" href="/">{escape(T['open_app'])}</a></p></section>
</article>"""
    ld = [app_entity(lang, subjects),
          {'@type': ['WebPage', 'AboutPage'], '@id': url(ABOUT[lang]) + '#page', 'url': url(ABOUT[lang]), 'name': T['about_title'],
           'description': T['summary'], 'inLanguage': lang, 'isPartOf': {'@id': f'{SITE}/#website'}, 'about': {'@id': f'{SITE}/#app'}},
          {'@type': 'FAQPage', '@id': url(ABOUT[lang]) + '#faq', 'inLanguage': lang, 'mainEntity': [
              {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faq]},
          breadcrumbs([(NAME, ''), (T['nav_about'], ABOUT[lang])])]
    return page(lang, T['about_title'], T['meta_desc'], ABOUT[lang], ABOUT, ld, css, 'about', body)


def goals_index(lang, subjects, css):
    T = TEXT[lang]
    rows = []
    for s in subjects:
        n = len(s['goals'])
        name = escape(s['name'][lang])
        rows.append(f'<li class="subject card" style="--c:var(--s-{s["key"].lower()})"><span class="dot"></span>'
                    + (f'<div><h2><a href="/{GOALS[lang]}/{s["slug"][lang]}/">{name}</a></h2><p class="muted">{escape(T["n_goals"](n))}</p></div>'
                       if n else f'<div><h2>{name}</h2><p class="muted">{escape(T["coming"])}</p></div>') + '</li>')
    body = f"""<article class="prose">
<h1>{escape(T['goals_h1'])}</h1>
<p class="lede">{escape(T['goals_lede'])} <a href="{SOURCE}" rel="noopener">onderwijsdoelen.be</a>.</p>
<ul class="subjects">{''.join(rows)}</ul>
</article>"""
    desc_ = T['goals_desc'](subject_list(subjects, lang))
    ld = [{'@type': 'CollectionPage', '@id': url(GOALS[lang]) + '#page', 'url': url(GOALS[lang]), 'name': T['goals_title'],
           'description': desc_, 'inLanguage': lang, 'isPartOf': {'@id': f'{SITE}/#website'},
           'mainEntity': {'@type': 'ItemList', 'itemListElement': [
               {'@type': 'ListItem', 'position': i, 'name': s['name'][lang], 'url': url(f'{GOALS[lang]}/{s["slug"][lang]}')}
               for i, s in enumerate((s for s in subjects if s['goals']), 1)]}},
          breadcrumbs([(NAME, ''), (T['nav_goals'], GOALS[lang])])]
    return page(lang, T['goals_title'], desc_, GOALS[lang], GOALS, ld, css, 'goals', body)


def subject_page(lang, s, subjects, css):
    T = TEXT[lang]
    name, n = s['name'][lang], len(s['goals'])
    path = f'{GOALS[lang]}/{s["slug"][lang]}'
    alternates = {l: f'{GOALS[l]}/{s["slug"][l]}' for l in ('nl', 'en')}
    sections = []
    for cat, goals in grouped(s['goals'], lang).items():
        items = ''.join(f'<li id="{anchor(g["code"])}"><code>{escape(g["code"])}</code><p>{escape(desc(g, lang))}</p>'
                        + (f'<p class="orig" lang="nl">{escape(g["description"])}</p>' if lang == 'en' and g.get('descriptionEn') else '')
                        + '</li>' for g in goals)
        sections.append(f'<section><h2>{escape(cat)}</h2><ol class="goals">{items}</ol></section>')
    others = ''.join(f'<li><a href="/{GOALS[lang]}/{o["slug"][lang]}/">{escape(o["name"][lang])}</a></li>' for o in subjects if o['goals'] and o is not s)
    body = f"""<article class="prose" style="--c:var(--s-{s['key'].lower()})">
<nav class="crumbs" aria-label="breadcrumb"><a href="/{GOALS[lang]}/">{escape(T['nav_goals'])}</a> › <span aria-current="page">{escape(name)}</span></nav>
<h1><span class="dot"></span>{escape(T['subject_h1'](name))}</h1>
<p class="lede">{escape(T['subject_lede'](name, n))}</p>
{''.join(sections)}
<p class="muted">{escape(T['source'])} <a href="{SOURCE}" rel="noopener">onderwijsdoelen.be</a>. {escape(T['disclaimer'])}</p>
<section class="card cta"><h2>{escape(T['cta_h'])}</h2><p>{escape(T['summary'])}</p><p><a class="btn primary" href="/">{escape(T['open_app'])}</a></p></section>
<section><h2>{escape(T['other_subjects'])}</h2><ul class="inline">{others}</ul></section>
</article>"""
    title = T['subject_title'](name)
    description = T['subject_desc'](name, n)
    term_set = {'@type': 'DefinedTermSet', '@id': url(path) + '#doelen', 'name': title, 'inLanguage': lang,
                'isBasedOn': SOURCE, 'educationalLevel': 'Kleuteronderwijs (preschool), Vlaanderen',
                'hasDefinedTerm': [{'@type': 'DefinedTerm', '@id': url(path) + '#' + anchor(g['code']), 'termCode': g['code'],
                                    'name': f'{g["code"]} {(g.get("categoryEn") if lang == "en" else None) or g.get("category", "")}'.strip(),
                                    'description': desc(g, lang), 'url': url(path) + '#' + anchor(g['code'])} for g in s['goals']]}
    ld = [{'@type': 'WebPage', '@id': url(path) + '#page', 'url': url(path), 'name': title, 'description': description,
           'inLanguage': lang, 'isPartOf': {'@id': f'{SITE}/#website'}, 'mainEntity': {'@id': url(path) + '#doelen'},
           'about': {'@type': 'Thing', 'name': name}},
          term_set, breadcrumbs([(NAME, ''), (T['nav_goals'], GOALS[lang]), (name, path)])]
    return page(lang, title, description, path, alternates, ld, css, 'goals', body)


def app_head(subjects):
    """The SEO part of the app page's <head> (index.html), filled in by build.py. Nothing in it shows
    in the page: the tab title stays the app's own <title>."""
    T = TEXT['nl']
    return f"""<meta name="description" content="{escape(T['meta_desc'])}">
<link rel="canonical" href="{SITE}/">
<link rel="alternate" hreflang="nl" href="{SITE}/">
<link rel="alternate" hreflang="x-default" href="{SITE}/">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
{social_meta('nl', T['app_title'], T['meta_desc'], f'{SITE}/')}<meta property="og:locale:alternate" content="en_GB">
{json_ld({'@context': 'https://schema.org', '@graph': [WEBSITE, app_entity('nl', subjects)]})}"""


def app_noscript():
    """Shown in the app page when JavaScript is off; also the text crawlers without JavaScript read."""
    T, E = TEXT['nl'], TEXT['en']
    def block(L, lang, h):
        return (f'<section lang="{lang}"><{h}>{escape(L["app_title"])}</{h}><p>{escape(L["summary"])}</p><p>{escape(L["noscript"])}</p>'
                f'<p><a href="/{ABOUT[lang]}/">{escape(L["nav_about"])}</a> · <a href="/{GOALS[lang]}/">{escape(L["nav_goals"])}</a></p></section>')
    return f'<noscript><div class="noscript card">{block(T, "nl", "h1")}{block(E, "en", "h2")}</div></noscript>'


def robots():
    return f"""# Doelenboek welcomes search engines and AI assistants: everything public may be crawled,
# indexed, quoted and used to answer questions. The app's own data sits behind a login and is
# never part of the pages.
User-agent: *
Allow: /

Sitemap: {SITE}/sitemap.xml
"""


def sitemap(subjects):
    pages = [{'nl': '', 'en': None}, dict(ABOUT), dict(GOALS)]
    pages += [{l: f'{GOALS[l]}/{s["slug"][l]}' for l in ('nl', 'en')} for s in subjects if s['goals']]
    out = []
    for alts in pages:
        for lang, p in alts.items():
            if p is None:
                continue
            links = ''.join(f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{url(q)}"/>' for l, q in alts.items() if q is not None)
            if alts.get('en') is not None:
                links += f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{url(alts["nl"])}"/>'
            out.append(f'  <url>\n    <loc>{url(p)}</loc>{links}\n  </url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + '\n'.join(out) + '\n</urlset>\n')


def llms_txt(subjects):
    """llms.txt (https://llmstxt.org): what the site is, in a form an AI assistant reads in one go."""
    T, E = TEXT['nl'], TEXT['en']
    subj_nl = '\n'.join(f'- [{s["name"]["nl"]}]({url(GOALS["nl"] + "/" + s["slug"]["nl"])}): {len(s["goals"])} minimumdoelen' for s in subjects if s['goals'])
    subj_en = '\n'.join(f'- [{s["name"]["en"]}]({url(GOALS["en"] + "/" + s["slug"]["en"])}): {len(s["goals"])} minimum goals' for s in subjects if s['goals'])
    faq = '\n\n'.join(f'### {q}\n\n{a.replace("{subjects}", subject_list(subjects, "en"))}' for q, a in E['faq'])
    return f"""# {NAME}

> {E['summary']}

Doelenboek ({SITE}) is a free web app in Dutch and English. Dutch summary: {T['summary']}

Key facts:

- Audience: parents who homeschool (huisonderwijs) in Flanders, Belgium
- Price: free, no ads; optional donations via Ko-fi ({KOFI})
- Platform: any web browser on computer, tablet or phone; account with email and password
- Goals included: the Flemish minimum goals (minimumdoelen) for preschool (kleuteronderwijs), for {subject_list(subjects, 'en')}, with their official codes, in Dutch and in English translation
- Official source of the goals: {SOURCE}
- Privacy: no cookies on the visitor's device; data stored in Google Firebase in the EU; users can delete their account and data at any time
- The app itself is at {SITE}/ and requires JavaScript and a login; the pages below are public

## About

- [Over Doelenboek (Dutch)]({url(ABOUT['nl'])}): what it is, how it works, questions and answers
- [About Doelenboek (English)]({url(ABOUT['en'])}): the same in English

## Minimumdoelen (Dutch)

- [Alle vakken]({url(GOALS['nl'])})
{subj_nl}

## Minimum goals (English)

- [All subjects]({url(GOALS['en'])})
{subj_en}

## Questions and answers

{faq}

## Optional

- [All goals in one file]({SITE}/llms-full.txt): every built-in minimum goal with code, category and text, in Dutch and English
"""


def llms_full(subjects):
    parts = [f'# {NAME}: the built-in Flemish minimum goals (minimumdoelen)\n\n> Every minimum goal for preschool '
             f'(kleuteronderwijs) included in {NAME} ({SITE}), the free homeschool tracker for Flanders. Official Dutch text '
             f'first, then the English translation. Official source: {SOURCE}. The completeness of this list is not guaranteed.\n']
    for s in subjects:
        if not s['goals']:
            continue
        parts.append(f'## {s["name"]["nl"]} ({s["name"]["en"]})\n\nPage: {url(GOALS["nl"] + "/" + s["slug"]["nl"])}\n')
        for cat, goals in grouped(s['goals'], 'nl').items():
            cat_en = goals[0].get('categoryEn')
            parts.append(f'### {cat}' + (f' ({cat_en})' if cat_en and cat_en != cat else '') + '\n')
            parts.append('\n'.join(f'- **{g["code"]}** {g["description"]}' + (f'\n  - EN: {g["descriptionEn"]}' if g.get('descriptionEn') else '') for g in goals) + '\n')
    return '\n'.join(parts)


def page_css(design):
    """tokens.css with the font URLs made absolute (the pages live in subfolders), then site.css."""
    tokens = (design / 'tokens.css').read_text(encoding='utf-8').replace('url("fonts/', 'url("/fonts/')
    return tokens.rstrip() + '\n' + (design / 'site.css').read_text(encoding='utf-8').rstrip()


def site_files(design, doelen_dir, subject_keys):
    """Every public page and crawler file, as {published path: text}."""
    subjects = load_subjects(doelen_dir, subject_keys)
    css = page_css(design)
    files = {}
    for lang in ('nl', 'en'):
        files[f'{ABOUT[lang]}/index.html'] = about_page(lang, subjects, css)
        files[f'{GOALS[lang]}/index.html'] = goals_index(lang, subjects, css)
        for s in subjects:
            if s['goals']:
                files[f'{GOALS[lang]}/{s["slug"][lang]}/index.html'] = subject_page(lang, s, subjects, css)
    files['robots.txt'] = robots()
    files['sitemap.xml'] = sitemap(subjects)
    files['llms.txt'] = llms_txt(subjects)
    files['llms-full.txt'] = llms_full(subjects)
    return files


COPIED = ('favicon.svg', 'og-image.png')   # from design/ to the site root as they are


def write_site(out_dir, design, doelen_dir, subject_keys):
    """Write every public page and crawler file into out_dir. Returns the paths written."""
    out_dir = Path(out_dir)
    files = site_files(design, doelen_dir, subject_keys)
    # the page of a subject whose goals were removed would linger: clear the generated folders first
    for lang in ('nl', 'en'):
        for d in (out_dir / ABOUT[lang], out_dir / GOALS[lang]):
            if d.is_dir():
                shutil.rmtree(d)
    for rel, text in files.items():
        p = out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8', newline='\n')
    for name in COPIED:
        shutil.copyfile(design / name, out_dir / name)
    return sorted(files) + list(COPIED)
