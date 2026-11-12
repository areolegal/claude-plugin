# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys,uuid,zlib
from datetime import date
SCHEMA_VERSION='1.0'
CORE_VERSION='2.1.0'
PRIMARY_DISPLAY=['הרשות להגנת הפרטיות','רשות התחרות','רשות ניירות ערך','רשות שוק ההון, ביטוח וחיסכון','בנק ישראל, הפיקוח על הבנקים','SEC','FCA','EDPB and the national data protection authorities · מפקחות על הגנת המידע האישי והעברתו באיחוד האירופי','ICO · מפקח על הגנת המידע האישי בבריטניה','FTC and the state privacy regulators · מפקחים על הגנת הצרכן והפרטיות בארצות הברית, פדרלית ובמדינות','רשם העמותות','רשם ההקדשות','המועצה להשכלה גבוהה ות״ת','רשות החברות הממשלתיות','משרד הפנים, הממונה על המחוז','Charity Commission','IRS, 501(c)(3)','Office for Students']
SEC_ISA={'מנהל תיקים','יועץ השקעות','משווק השקעות','מנהל קרנות נאמנות','מנהל קרנות נאמנות או השקעה','חתם','נאמן לאיגרות חוב','זירת סוחר','מימון המונים','רכז הצעה, מימון המונים','חברת דירוג אשראי','חבר בורסה'}
CMISA={'מבטח','סוכן ביטוח','קרן פנסיה או גמל','נותן שירותים פיננסיים מוסדר','אשראי חוץ בנקאי','ניכיון צ׳קים',"ניכיון צ'קים",'נותן שירות בנכס פיננסי (כולל נכסים דיגיטליים)','נותן שירות בנכס פיננסי','שירותי תשלום וסליקה'}
BOI={'תאגיד בנקאי','חברת כרטיסי אשראי'}
FIN_POTENTIAL={'ליסינג':'רשות שוק ההון, ביטוח וחיסכון','שירותי תשלום וסליקה':'בנק ישראל, הפיקוח על הבנקים'}
SECTOR_REGULATORS={'ביטוח':['רשות שוק ההון, ביטוח וחיסכון'],'אנרגיה':['רשות החשמל','משרד האנרגיה','המשרד להגנת הסביבה'],'ביומד':['משרד הבריאות','רשות החדשנות'],'בריאות':['משרד הבריאות'],'מזון ומשקאות':['משרד הבריאות','הרשות להגנת הצרכן ולסחר הוגן'],'תקשורת ומדיה':['משרד התקשורת'],'נדל״ן':['רשם הקבלנים','רשות מקרקעי ישראל'],'בנייה ותשתיות':['רשם הקבלנים','רשות מקרקעי ישראל','המשרד להגנת הסביבה'],'ביטחון ותעופה':['אפ״י','BIS and DDTC · מפקחים על בקרת היצוא הביטחוני והדו-שימושי של ארצות הברית'],'תחבורה ולוגיסטיקה':['משרד התחבורה'],'חינוך':['משרד החינוך','הרשות להגנת הצרכן ולסחר הוגן'],'קמעונאות':['הרשות להגנת הצרכן ולסחר הוגן'],'תיירות ומלונאות':['הרשות להגנת הצרכן ולסחר הוגן'],'תעשייה':['המשרד להגנת הסביבה','רשות החדשנות'],'הייטק':['רשות החדשנות'],'סייבר':['רשות החדשנות']}
SECTOR_NOT_IL={'BIS and DDTC · מפקחים על בקרת היצוא הביטחוני והדו-שימושי של ארצות הברית'}
SECTOR_IL_MARKET_ONLY={'רשם הקבלנים','רשות מקרקעי ישראל'}
MARKET_REGULATORS={'האיחוד האירופי':[('EDPB and the national data protection authorities · מפקחות על הגנת המידע האישי והעברתו באיחוד האירופי','Likely'),('European AI Office · מפקח על פיתוח ושימוש במערכות בינה מלאכותית באיחוד האירופי','Likely')],'בריטניה':[('ICO · מפקח על הגנת המידע האישי בבריטניה','Potential'),('SFO · חוקר ותובע שוחד ומרמה חמורה בבריטניה','Likely')],'ארצות הברית':[('FTC and the state privacy regulators · מפקחים על הגנת הצרכן והפרטיות בארצות הברית, פדרלית ובמדינות','Potential'),('DOJ · אוכף את איסור השוחד של גורמים זרים','Likely'),('OFAC','Likely'),('BIS','Likely')]}
CORPORATE_REGULATORS={'חברה ממשלתית':[('רשות החברות הממשלתיות','Likely')],'עמותה':[('רשם העמותות','Likely')],'חל״צ (חברה לתועלת הציבור)':[('רשם ההקדשות','Likely')],'הקדש או מלכ״ר':[('רשם ההקדשות','Potential')],'מוסד להשכלה גבוהה או אוניברסיטה':[('המועצה להשכלה גבוהה ות״ת','Likely')],'גוף ציבורי או משרד ממשלתי':[],'רשות מקומית':[('משרד הפנים, הממונה על המחוז','Likely','corp_local')],'תאגיד סטטוטורי':[],'שותפות':[('רשם השותפויות, רשות התאגידים','Confirmed')],'אגודה שיתופית':[('רשם האגודות השיתופיות','Confirmed')],'עמותה או חל״צ':[('רשם העמותות','Likely'),('רשם ההקדשות','Potential')],'גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)':[]}
NONPROFIT_FORMS={'עמותה','חל״צ (חברה לתועלת הציבור)','הקדש או מלכ״ר','עמותה או חל״צ'}
HIGHER_ED_FORMS={'מוסד להשכלה גבוהה או אוניברסיטה'}
FOREIGN_FORM_REGULATORS=[(NONPROFIT_FORMS,'GB','בריטניה','Charity Commission'),(NONPROFIT_FORMS|HIGHER_ED_FORMS,'US','ארצות הברית','IRS, 501(c)(3)'),(HIGHER_ED_FORMS,'GB','בריטניה','Office for Students')]
NON_COMPANY_FORMS={'עמותה','הקדש או מלכ״ר','גוף ציבורי או משרד ממשלתי','רשות מקומית','תאגיד סטטוטורי','גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)','שותפות','אגודה שיתופית'}
PUBLIC_FORMS={'חברה ממשלתית','גוף ציבורי או משרד ממשלתי','רשות מקומית','תאגיד סטטוטורי','מוסד להשכלה גבוהה או אוניברסיטה','גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)'}
VENUE_REGULATORS={'TASE':[('רשות ניירות ערך','Confirmed'),('הבורסה לניירות ערך בתל אביב','Confirmed')],'NASDAQ':[('SEC','Confirmed')],'NYSE':[('SEC','Confirmed')],'LSE':[('FCA','Confirmed')],'FSE':[('BaFin','Confirmed')]}
COUNTRY_CODES={'ישראל':'IL','israel':'IL','isr':'IL','מדינת ישראל':'IL','state of israel':'IL','ארצות הברית':'US','ארה״ב':'US','ארה"ב':'US','united states':'US','usa':'US','us':'US','united states of america':'US','america':'US','בריטניה':'GB','אנגליה':'GB','הממלכה המאוחדת':'GB','united kingdom':'GB','uk':'GB','gbr':'GB','great britain':'GB','britain':'GB','england':'GB','england and wales':'GB','wales':'GB','scotland':'GB','northern ireland':'GB','סקוטלנד':'GB','ויילס':'GB','צפון אירלנד':'GB','גרמניה':'DE','germany':'DE','deu':'DE','צרפת':'FR','france':'FR','fra':'FR','הולנד':'NL','netherlands':'NL','the netherlands':'NL','holland':'NL','nld':'NL','אירלנד':'IE','ireland':'IE','irl':'IE','republic of ireland':'IE','קפריסין':'CY','cyprus':'CY','cyp':'CY','איטליה':'IT','italy':'IT','ita':'IT','ספרד':'ES','spain':'ES','esp':'ES','פורטוגל':'PT','portugal':'PT','prt':'PT','בלגיה':'BE','belgium':'BE','bel':'BE','לוקסמבורג':'LU','luxembourg':'LU','lux':'LU','אוסטריה':'AT','austria':'AT','aut':'AT','שוודיה':'SE','sweden':'SE','swe':'SE','דנמרק':'DK','denmark':'DK','dnk':'DK','פינלנד':'FI','finland':'FI','fin':'FI','פולין':'PL','poland':'PL','pol':'PL',"צ'כיה":'CZ','צכיה':'CZ','czechia':'CZ','czech republic':'CZ','cze':'CZ','יוון':'GR','greece':'GR','grc':'GR','הונגריה':'HU','hungary':'HU','hun':'HU','רומניה':'RO','romania':'RO','rou':'RO','בולגריה':'BG','bulgaria':'BG','bgr':'BG','קרואטיה':'HR','croatia':'HR','hrv':'HR','סלובקיה':'SK','slovakia':'SK','svk':'SK','סלובניה':'SI','slovenia':'SI','svn':'SI','אסטוניה':'EE','estonia':'EE','est':'EE','לטביה':'LV','latvia':'LV','lva':'LV','ליטא':'LT','lithuania':'LT','ltu':'LT','מלטה':'MT','malta':'MT','mlt':'MT','שווייץ':'CH','שוויץ':'CH','switzerland':'CH','che':'CH','נורווגיה':'NO','norway':'NO','nor':'NO','קנדה':'CA','canada':'CA','can':'CA','אוסטרליה':'AU','australia':'AU','aus':'AU','ניו זילנד':'NZ','new zealand':'NZ','סינגפור':'SG','singapore':'SG','sgp':'SG','הונג קונג':'HK','hong kong':'HK','hkg':'HK','הודו':'IN','india':'IN','ind':'IN','סין':'CN','china':'CN','chn':'CN','יפן':'JP','japan':'JP','jpn':'JP','דרום קוריאה':'KR','south korea':'KR','korea':'KR','kor':'KR','איחוד האמירויות':'AE','איחוד האמירויות הערביות':'AE','united arab emirates':'AE','uae':'AE','are':'AE','איי קיימן':'KY','cayman islands':'KY','cym':'KY','איי הבתולה הבריטיים':'VG','british virgin islands':'VG','bvi':'VG','vgb':'VG',"ג'רזי":'JE','jersey':'JE','גרנזי':'GG','guernsey':'GG','האי מאן':'IM','isle of man':'IM','גיברלטר':'GI','gibraltar':'GI','ברמודה':'BM','bermuda':'BM','דרום אפריקה':'ZA','south africa':'ZA','ברזיל':'BR','brazil':'BR','מקסיקו':'MX','mexico':'MX','טורקיה':'TR','turkey':'TR','türkiye':'TR','turkiye':'TR','אוקראינה':'UA','ukraine':'UA'}
ALPHA2_ALIASES={'UK':'GB','EL':'GR'}
EU_MEMBERS={'AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR','DE','GR','HU','IE','IT','LV','LT','LU','MT','NL','PL','PT','RO','SK','SI','ES','SE'}
US_STATES={'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO','connecticut':'CT','delaware':'DE','florida':'FL','hawaii':'HI','idaho':'ID','illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV','new hampshire':'NH','new jersey':'NJ','new mexico':'NM','new york':'NY','north carolina':'NC','north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA','rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN','texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA','west virginia':'WV','wisconsin':'WI','wyoming':'WY','district of columbia':'DC','washington dc':'DC','washington d.c':'DC','washington, d.c':'DC','washington, dc':'DC','דלאוור':'DE','דלוור':'DE','דלאוואר':'DE','ניו יורק':'NY','קליפורניה':'CA','טקסס':'TX','פלורידה':'FL',"מסצ'וסטס":'MA','מסצ׳וסטס':'MA',"ניו ג'רזי":'NJ','ניו ג׳רזי':'NJ','נבדה':'NV','אילינוי':'IL','וושינגטון':'WA','ויומינג':'WY','קולורדו':'CO','פנסילבניה':'PA',"וירג'יניה":'VA','מרילנד':'MD','קונטיקט':'CT','מישיגן':'MI','אוהיו':'OH','יוטה':'UT'}
GB_JURISDICTIONS={'england':'GB-EAW','wales':'GB-EAW','england and wales':'GB-EAW','אנגליה':'GB-EAW','ויילס':'GB-EAW','אנגליה ווילס':'GB-EAW','אנגליה ויילס':'GB-EAW','scotland':'GB-SCT','סקוטלנד':'GB-SCT','northern ireland':'GB-NIR','צפון אירלנד':'GB-NIR'}
COUNTRY_NAMES={}
for(_k,_c)in COUNTRY_CODES.items():
	_n=COUNTRY_NAMES.setdefault(_c,{})
	if re.search('[\\u0590-\\u05ff]',_k):_n.setdefault('he',_k)
	elif len(_k)>3 and re.fullmatch("[a-z .'-]+",_k):_n.setdefault('en',' '.join(A if A in('and','of')else A.capitalize()for A in _k.split()))
MARKET_CODES={'ישראל':'IL','האיחוד האירופי':'EU','בריטניה':'GB','ארצות הברית':'US'}
MARKET_ROW={'EU':'האיחוד האירופי','GB':'בריטניה','US':'ארצות הברית'}
EU_NAMES={'eu','european union','האיחוד האירופי','איחוד אירופי','אירופה','europe','eea'}
NOT_LISTED={'לא נסחרת','לא','not traded','not listed','none','no','-'}
STATUS_LABELS={'he':{'Confirmed':'מאומת','Likely':'סביר','Potential':'אפשרי','UserDeclared':'הוצהר על ידכם'},'en':{'Confirmed':'Verified','Likely':'Likely','Potential':'Possible','UserDeclared':'Declared by you'}}
LOGO_LABELS={'he':{'attached':'צורף','later':'יתווסף מאוחר יותר','none':'בלי לוגו'},'en':{'attached':'Attached','later':'To be added later','none':'No logo'}}
EN_LABELS={'country':{'ישראל':'Israel','ארצות הברית':'United States','בריטניה':'United Kingdom','גרמניה':'Germany','צרפת':'France','הולנד':'Netherlands','אירלנד':'Ireland','קפריסין':'Cyprus'},'form':{'חברה פרטית':'Private company','חברה ציבורית (נסחרת בבורסה)':'Public company (listed on a stock exchange)','חברת אג״ח (גייסה אג״ח לציבור)':'Bond issuer (raised bonds from the public)','חברה ממשלתית':'Government company','גוף ציבורי או משרד ממשלתי':'Public body or government ministry','רשות מקומית':'Local authority (municipality or local council)','תאגיד סטטוטורי':'Statutory corporation','מוסד להשכלה גבוהה או אוניברסיטה':'University or higher education institution','עמותה':'Non-profit association (amuta)','חל״צ (חברה לתועלת הציבור)':'Public benefit company (PBC)','הקדש או מלכ״ר':'Charity, trust, foundation or other non-profit','חברת חוץ (חברה זרה הרשומה בישראל)':'Foreign company registered in Israel','חברה זרה (לא רשומה בישראל)':'Foreign company (not registered in Israel)','שותפות':'Partnership','אגודה שיתופית':'Cooperative society','גוף ציבורי (משרד ממשלתי, רשות מקומית, תאגיד סטטוטורי)':'Public body (government ministry, local authority, statutory corporation)','עמותה או חל״צ':'Non-profit association or public benefit company'},'listed':{'ישראל':'Israel (TASE)','נאסד״ק':'Nasdaq','ניו יורק (NYSE)':'New York (NYSE)','לונדון':'London','רישום דואלי':'Dual listing'},'dual':{'נאסד״ק':'Nasdaq','ניו יורק (NYSE)':'New York (NYSE)','לונדון (LSE)':'London (LSE)','פרנקפורט':'Frankfurt'},'sector':{'הייטק':'High-tech','פינטק':'Fintech','פיננסים':'Finance','ביטוח':'Insurance','אנרגיה':'Energy','שירותים':'Services','נדל״ן':'Real estate','ביומד':'Biomed','בריאות':'Healthcare','תעשייה':'Industry','קמעונאות':'Retail','תקשורת ומדיה':'Telecom and media','תחבורה ולוגיסטיקה':'Transport and logistics','מזון ומשקאות':'Food and beverages','בנייה ותשתיות':'Construction and infrastructure','ביטחון ותעופה':'Defense and aerospace','סייבר':'Cyber','חקלאות':'Agriculture','חינוך':'Education','תיירות ומלונאות':'Tourism and hospitality','השכלה גבוהה ומחקר':'Higher education and research','רווחה וקהילה':'Welfare and community','שירותים ציבוריים ושלטון מקומי':'Public services and local government'},'fin':{'מנהל תיקים':'Portfolio manager','יועץ השקעות':'Investment adviser','משווק השקעות':'Investment marketer','מנהל קרנות נאמנות':'Mutual fund manager','חתם':'Underwriter','נאמן לאיגרות חוב':'Bond trustee','זירת סוחר':'Trading platform (forex and CFD)','מימון המונים':'Crowdfunding (offering coordinator)','רכז הצעה, מימון המונים':'Crowdfunding (offering coordinator)','חברת דירוג אשראי':'Credit rating agency','מבטח':'Insurer','מנהל קרנות נאמנות או השקעה':'Mutual or investment fund manager','חבר בורסה':'Stock exchange member','סוכן ביטוח':'Insurance agent','אשראי חוץ בנקאי':'Non-bank credit provider','ניכיון צ׳קים':'Cheque discounting',"ניכיון צ'קים":'Cheque discounting','נותן שירות בנכס פיננסי (כולל נכסים דיגיטליים)':'Financial asset service provider (incl. digital assets)','נותן שירות בנכס פיננסי':'Financial asset service provider','שירותי תשלום וסליקה':'Payment and clearing services','ליסינג':'Leasing','קרן פנסיה או גמל':'Pension or provident fund','נותן שירותים פיננסיים מוסדר':'Regulated financial services provider','תאגיד בנקאי':'Banking corporation','חברת כרטיסי אשראי':'Credit card company'},'market':{'ישראל':'Israel','האיחוד האירופי':'European Union','בריטניה':'United Kingdom','ארצות הברית':'United States'},'logo':{'אעלה עכשיו':'Upload now','אוסיף מאוחר יותר':'Add later','בלי לוגו':'No logo'},'brand':{'כן':'Yes','לא':'No'}}
REG_EN={'הרשות להגנת הפרטיות':'Privacy Protection Authority (Israel)','רשות התחרות':'Israel Competition Authority','רשות ניירות ערך':'Israel Securities Authority','רשות שוק ההון, ביטוח וחיסכון':'Capital Market, Insurance and Savings Authority (Israel)','בנק ישראל, הפיקוח על הבנקים':'Bank of Israel, Banking Supervision Department','EDPB and the national data protection authorities · מפקחות על הגנת המידע האישי והעברתו באיחוד האירופי':'EDPB and the national data protection authorities','FTC and the state privacy regulators · מפקחים על הגנת הצרכן והפרטיות בארצות הברית, פדרלית ובמדינות':'FTC and the state privacy regulators','רשות המסים':'Israel Tax Authority','רשם החברות, רשות התאגידים':'Registrar of Companies, Israel Corporations Authority','משרד העבודה, מינהל הסדרה ואכיפה':'Ministry of Labor, Regulation and Enforcement Administration','המוסד לביטוח לאומי':'National Insurance Institute','נציבות שוויון זכויות לאנשים עם מוגבלות':'Commission for Equal Rights of Persons with Disabilities','הבורסה לניירות ערך בתל אביב':'Tel Aviv Stock Exchange','רשות החברות הממשלתיות':'Government Companies Authority','רשם העמותות':'Registrar of Non-profit Associations','רשם השותפויות, רשות התאגידים':'Registrar of Partnerships, Israel Corporations Authority','רשם האגודות השיתופיות':'Registrar of Cooperative Societies','רשות החשמל':'Electricity Authority','משרד האנרגיה':'Ministry of Energy','המשרד להגנת הסביבה':'Ministry of Environmental Protection','משרד הבריאות':'Ministry of Health','רשות החדשנות':'Israel Innovation Authority','הרשות להגנת הצרכן ולסחר הוגן':'Consumer Protection and Fair Trade Authority','משרד התקשורת':'Ministry of Communications','רשם הקבלנים':'Registrar of Contractors','רשות מקרקעי ישראל':'Israel Land Authority','אפ״י':'Defense Export Controls Agency (DECA)','BIS and DDTC · מפקחים על בקרת היצוא הביטחוני והדו-שימושי של ארצות הברית':'BIS and DDTC','משרד התחבורה':'Ministry of Transport','משרד החינוך':'Ministry of Education','European AI Office · מפקח על פיתוח ושימוש במערכות בינה מלאכותית באיחוד האירופי':'European AI Office','SFO · חוקר ותובע שוחד ומרמה חמורה בבריטניה':'SFO','DOJ · אוכף את איסור השוחד של גורמים זרים':'DOJ','ICO · מפקח על הגנת המידע האישי בבריטניה':'ICO','רשם ההקדשות':'Registrar of Endowments (Israel)','המועצה להשכלה גבוהה ות״ת':'Council for Higher Education and its Planning and Budgeting Committee (Israel)','משרד הפנים, הממונה על המחוז':'Ministry of Interior, District Commissioner (Israel)','Charity Commission':'Charity Commission (UK)','IRS, 501(c)(3)':'IRS, section 501(c)(3) (US)','Office for Students':'Office for Students (UK)'}
REG_HE={B.casefold():A for(A,B)in REG_EN.items()}
CATALOG_EN={'הגנת הפרטיות ואבטחת מידע':'Privacy and data security','שימוש במערכת AI':'AI system use','איסור שוחד':'Anti-bribery','סנקציות':'Sanctions','בקרת יצוא':'Export controls','פרטיות לפי דין מקומי':'Local-law privacy','עיבוד מידע אישי על ידי צד שלישי':'Personal-data processing by a third party','העברת מידע אישי בין מדינות':'Cross-border personal-data transfer','התחייבויות כלפי מחזיקי ניירות ערך ואמות מידה פיננסיות':'Obligations to securities holders and financial covenants','ציות רגולטורי פיננסי':'Financial regulatory compliance','גילוי מכוח כללי שקיפות לציבור':'Disclosure under public-access rules','כללי רכש והליך תחרותי':'Public procurement and competitive-procedure rules','תקציב והתחייבות לתקופה':'Budget appropriation and multi-year commitment','כספי תרומות ודיווח לרשם':'Restricted donor funds and reporting to the registrar'}
T={'he':{'privacy':'הגנת הפרטיות; %s','il_axis':'%s','nx_inc':'התאגדות בישראל','nx_foreign':'רישום כחברת חוץ בישראל','nx_market':'שוק פעילות: ישראל','corp':'צורת ההתאגדות: %s','corp_inc':'צורת ההתאגדות: %s, התאגדות ב%s','corp_mkt':'צורת ההתאגדות: %s; שוק פעילות: %s','corp_local':'צורת ההתאגדות: %s; רשות מקומית','bond':'חברת אג״ח, כתאגיד מדווח','dual':'רישום כפול','dual_on':'רישום דואלי ב%s','listed_on':'נסחרת ב%s','fin':'עיסוק מפוקח: %s','sector':'ענף פעילות: %s','market':'שוק פעילות: %s','fin_mkt':'עיסוק מפוקח: %s; שוק פעילות: ישראל, בלי התאגדות או רישום בישראל','geo_inc':'מדינת ההתאגדות: %s','declared':'הוצהר על ידכם בהקמה','q_country':'מדינת ההתאגדות לא נמסרה או אינה מוכרת, ולכן חסרים הרגולטורים שתלויים בה ובצורת ההתאגדות. מסרו את מדינת ההתאגדות כדי להשלים אותם.','q_dual':'נבחר רישום דואלי בלי הבורסות הזרות, ולכן הרגולטור שלהן לא זוהה. מסרו באילו בורסות.','q_fin':'עיסוק פיננסי (%s) מחוץ לישראל: הרגולטור שלו אינו ברשימה. אפשר להוסיף אותו ידנית.','q_signer':'שם החותם על המסמכים היוצאים לא נמסר.','q_market':'שוק פעילות %s: אין לו רגולטור ברשימה, ולכן לא נוסף רגולטור. אפשר להוסיף אחד ידנית.','q_regno':'מספר הרישום %s אינו עובר את בדיקת ספרת הביקורת. בדקו אותו.','q_name_en':'השם הרשום באנגלית לא נמסר. בהסכם באנגלית הוא יידרש.','q_title':'**שאלות פתוחות** (אפשר לענות עליהן עכשיו, או לאשר ולהשלים אחר כך)','kept':'כמו בפרופיל הקודם: העובדות שעליהן הוא נשען לא השתנו','chg_title':'**מה משתנה ברגולטורים**','chg':'%s: היה %s, עכשיו %s','chg_add':'%s: נוסף, %s','chg_del':'%s: יורד מהרשימה','pv':'תצוגה מקדימה: הפרופיל עוד לא נשמר.','upd':'הפרופיל עודכן.','saved':'הפרופיל נשמר.','openq':'שאלה פתוחה: %s','set_line':'%s: %s, במקום %s','set_new':'%s: %s','fields':{'display_language':'שפת הממשק','deliverable_language':'שפת התוצרים','deliverable_language_basis':'הבסיס לשפת התוצרים','organization_name_en':'השם הרשום באנגלית','registration_number':'מספר הרישום','branding.signatories':'מורשי החתימה','branding.policy_approver':'מאשר המדיניות','branding.lawyer_name':'החותם','branding.website':'אתר החברה','branding.theme':'המיתוג','branding.logo_path':'הלוגו','branding.logo_status':'הלוגו','branding.logo_added_at':'הלוגו','departments_involved':'המחלקות המעורבות','connections':'החיבורים'},'langs':{'he':'עברית','en':'אנגלית','both':'עברית ואנגלית'},'none':'לא נמסר','confidential':'חסוי: הוכן לצורך קבלת ייעוץ משפטי','type_basis':'הצהרת המשתמש בהקמה','method':'הצהרת המשתמש בלבד, בלי מחקר רשת','note':'הפרופיל שומר זהות רגולטורים בלבד, ולא תוכן חובות.','title':'**תקציר הפרופיל לאישור**','head':'| שדה | ערך |','r_name':'שם ומספר רישום','v_name':'%s, מספר רישום %s','r_country':'מדינת התאגדות','r_name_en':'שם רשום באנגלית','v_name_en_none':'לא נמסר (לא חובה)','r_form':'צורת התאגדות','r_listed':'היכן נסחרת','r_sectors':'תחומי פעילות','r_desc':'תיאור הפעילות','r_markets':'שווקים','r_signer':'חותם על המסמכים היוצאים','r_lang':'שפת ממשק','v_lang':{'he':'עברית','en':'אנגלית'},'r_logo':'לוגו','r_site':'אתר החברה','r_brand':'מיתוג סביבות העבודה בצבעי המותג','v_yesno':{'yes':'כן','no':'לא'},'missing':'לא נמסר','not_listed':'לא נסחרת','regs':'**רגולטורים עיקריים** (לפי התשובות שלכם)','regs_head':'| רגולטור | מעמד | על סמך |','no_regs':'| לפי התשובות, אף רגולטור מהרשימה אינו חל | | |'},'en':{'privacy':'Privacy protection; %s','il_axis':'%s','nx_inc':'Incorporated in Israel','nx_foreign':'Registered in Israel as a foreign company','nx_market':'Market: Israel','corp':'Legal form: %s','corp_inc':'Legal form: %s, incorporated in %s','corp_mkt':'Legal form: %s; market: %s','corp_local':'Legal form: %s; local authority','bond':'Bond issuer, as a reporting corporation','dual':'Dual listing','dual_on':'Dual listing on: %s','listed_on':'Listed on: %s','fin':'Regulated activity: %s','sector':'Sector: %s','market':'Market: %s','fin_mkt':'Regulated activity: %s; market: Israel, without incorporation or registration in Israel','geo_inc':'Country of incorporation: %s','declared':'Declared by you at setup','q_country':'The country of incorporation was not given or is not recognized, so the regulators that depend on it and on the legal form are missing. Give the country of incorporation to complete them.','q_dual':'Dual listing was selected without the foreign exchanges, so their regulator was not identified. Give the exchanges.','q_fin':'Financial activity (%s) outside Israel: its regulator is not on the list. You can add it yourself.','q_signer':'The signer of outgoing documents was not given.','q_market':'Market %s: no regulator on the list, so none was added. You can add one yourself.','q_regno':'The registration number %s fails the check digit. Check it.','q_name_en':'The registered English name was not given. An English agreement will need it.','q_title':'**Open questions** (answer them now, or approve and complete them later)','kept':'As in the previous profile: the facts it rests on did not change','chg_title':'**What changes in the regulators**','chg':'%s: was %s, now %s','chg_add':'%s: added, %s','chg_del':'%s: leaves the list','pv':'Preview only: the profile is not saved yet.','upd':'The profile is updated.','saved':'The profile is saved.','openq':'Open question: %s','set_line':'%s: %s (was %s)','set_new':'%s: %s','fields':{'display_language':'Interface language','deliverable_language':'Output language','deliverable_language_basis':'Basis for the output language','organization_name_en':'Registered English name','registration_number':'Registration number','branding.signatories':'Signatories','branding.lawyer_name':'Signer','branding.policy_approver':'Policy approver','branding.website':'Company website','branding.theme':'Branding','branding.logo_path':'Logo','branding.logo_status':'Logo','branding.logo_added_at':'Logo','departments_involved':'Departments involved','connections':'Connections'},'langs':{'he':'Hebrew','en':'English','both':'Hebrew and English'},'none':'not given','confidential':'Privileged and confidential: prepared for the purpose of obtaining legal advice','type_basis':'Declared by the user at setup','method':'User declaration only, no web research','note':'The profile records the identity of regulators only, not the content of obligations.','title':'**Profile summary for approval**','head':'| Field | Value |','r_name':'Name and registration number','v_name':'%s, registration number %s','r_name_en':'Registered name in English','v_name_en_none':'Not given (optional)','r_country':'Country of incorporation','r_form':'Legal form','r_listed':'Where traded','r_sectors':'Sectors','r_desc':'Activity description','r_markets':'Markets','r_signer':'Signer of outgoing documents','r_lang':'Interface language','v_lang':{'he':'Hebrew','en':'English'},'r_logo':'Logo','r_site':'Company website','r_brand':'Brand the workspaces in your brand colours','v_yesno':{'yes':'Yes','no':'No'},'missing':'Not given','not_listed':'Not traded','regs':'**Primary regulators** (based on your answers)','regs_head':'| Regulator | Status | Basis |','no_regs':'| Based on your answers, no regulator on the list applies | | |'}}
FIELD_LABELS={'incorporation_country':'country','organization_type':'form','listed_in':'listed','dual_listed_in':'dual','sectors':'sector','financial_activity':'fin','markets':'market','logo':'logo','brand_theme':'brand'}
def canon(kind,v):
	A=str(v or'').strip();B=EN_LABELS.get(kind,{})
	if A in B:return A
	C=A.casefold();return next((A for(A,B)in B.items()if B.casefold()==C),A)
def label(kind,v,lang):
	B=lang;A=kind
	if v in EN_LABELS.get(A,{}):return EN_LABELS[A][v]if B=='en'else v
	if A in('country','market')and v:
		C=market_code(v)if A=='market'else country_code(v)
		if C=='EU':return EN_LABELS['market']['האיחוד האירופי']if B=='en'else'האיחוד האירופי'
		if A=='country'and parse_country(v)[1]:return v
		D=(COUNTRY_NAMES.get(C)or{}).get(B)
		if D:return D
	return v
def market_code(m):
	A=str(m or'').strip()
	if A in MARKET_CODES:return MARKET_CODES[A]
	if A.casefold()in EU_NAMES or canon('market',A)=='האיחוד האירופי':return'EU'
	B=canon('market',A)
	if B in MARKET_CODES:return MARKET_CODES[B]
	return country_code(A)
def market_row(code):
	if code in EU_MEMBERS:return MARKET_ROW['EU']
	return MARKET_ROW.get(code)
def reg_label(name,lang):A=name;return REG_EN.get(A,A)if lang=='en'else A
CATALOG_TRIGGERS=[(lambda a:True,['הגנת הפרטיות ואבטחת מידע']),(lambda a:'האיחוד האירופי'in geo_markets(a),['עיבוד מידע אישי על ידי צד שלישי','העברת מידע אישי בין מדינות','שימוש במערכת AI']),(lambda a:'בריטניה'in geo_markets(a),['עיבוד מידע אישי על ידי צד שלישי','העברת מידע אישי בין מדינות','איסור שוחד']),(lambda a:'ארצות הברית'in geo_markets(a),['סנקציות','בקרת יצוא','פרטיות לפי דין מקומי']),(lambda a:a['organization_type'].startswith('חברת אג״ח'),['התחייבויות כלפי מחזיקי ניירות ערך ואמות מידה פיננסיות']),(lambda a:bool(a['financial_activity']),['ציות רגולטורי פיננסי']),(lambda a:a['organization_type']in PUBLIC_FORMS,['גילוי מכוח כללי שקיפות לציבור','כללי רכש והליך תחרותי','תקציב והתחייבות לתקופה']),(lambda a:a['organization_type']in NONPROFIT_FORMS,['כספי תרומות ודיווח לרשם'])]
CATALOG_CONDITIONS={'personal_data':{'he':'חל רק על הסכם שבו צד מעבד, מקבל, מעביר או ניגש למידע אישי, לפי הפלייבוק או ההסכם עצמו','en':'Applies only to an agreement under which a party processes, receives, transfers or accesses personal data, according to the playbook or the agreement itself'},'ai':{'he':'חל רק על הסכם שיש בו פיתוח, אספקה או שימוש במערכת AI, לפי הפלייבוק או ההסכם עצמו','en':'Applies only to an agreement that involves developing, supplying or using an AI system, according to the playbook or the agreement itself'}}
CATALOG_CONDITION_OF={'הגנת הפרטיות ואבטחת מידע':'personal_data','עיבוד מידע אישי על ידי צד שלישי':'personal_data','העברת מידע אישי בין מדינות':'personal_data','פרטיות לפי דין מקומי':'personal_data','שימוש במערכת AI':'ai'}
def _country_key(s):s=re.sub('\\s+',' ',str(s or'').replace('״','"').replace('׳',"'").strip().strip('.')).casefold();return re.sub('^(the|state of|commonwealth of) ','',s)
def _lookup_country(part):
	B=_country_key(part)
	if not B:return None,None
	if re.fullmatch('[a-z]{2}',B):E=B.upper();return ALPHA2_ALIASES.get(E,E),None
	C=re.fullmatch('([a-z]{2})-([a-z]{2,3})',B)
	if C:F=ALPHA2_ALIASES.get(C.group(1).upper(),C.group(1).upper());return F,'%s-%s'%(F,C.group(2).upper())
	D=B,B.replace('"','״'),B.replace("'",'׳')
	for A in D:
		if A in GB_JURISDICTIONS:return'GB',GB_JURISDICTIONS[A]
	for A in D:
		if A in COUNTRY_CODES:return COUNTRY_CODES[A],None
	for A in D:
		if A in US_STATES:return'US','US-'+US_STATES[A]
	return None,None
def parse_country(raw):
	C=(raw or'').strip()
	if not C:return None,None
	A,B=_lookup_country(C)
	if A:return A,B
	for E in re.split('\\s*[,()/;]\\s*|\\s+-\\s+',C):
		D,F=_lookup_country(E)
		if D and A in(None,D):A,B=D,B or F
	return A,B
def country_code(raw):return parse_country(raw)[0]
def venue_code(raw):
	A=(raw or'').lower()
	if'דואלי'in A or'dual'in A:return'DUAL'
	if'nyse'in A or'ניו יורק'in A:return'NYSE'
	if'נאסד'in A or'nasdaq'in A:return'NASDAQ'
	if'לונדון'in A or'london'in A or'lse'in A:return'LSE'
	if'פרנקפורט'in A or'frankfurt'in A:return'FSE'
	if'ישראל'in A or'תל אביב'in A or'tase'in A or'israel'in A or'tel aviv'in A:return'TASE'
def add(reg_list,name,status,basis):
	D=basis;C=reg_list;B=status
	for A in C:
		if A['regulator_name']==name:
			E={'Confirmed':0,'Likely':1,'Potential':2,'UserDeclared':3}
			if E[B]<E[A['applicability_status']]:A['applicability_status']=B;A['basis']=D
			return
	C.append({'regulator_name':name,'applicability_status':B,'basis':D})
IL_REGISTERED_FORMS={'חברת חוץ (חברה זרה הרשומה בישראל)','עמותה','חל״צ (חברה לתועלת הציבור)','חברה ממשלתית','אגודה שיתופית','עמותה או חל״צ'}
def il_check_digit(num):
	if not re.fullmatch('\\d{9}',num):return True
	B=0
	for(C,D)in enumerate(num):A=int(D)*(1 if C%2==0 else 2);B+=A-9 if A>9 else A
	return B%10==0
def nexus(a):
	A=country_code(a.get('incorporation_country'));B=any(market_code(A)=='IL'for A in a['markets']);C=a['organization_type'].startswith('חברת חוץ')
	if A=='IL':return A,True,B,'nx_inc'
	if C:return A,True,B,'nx_foreign'
	if B:return A,False,True,'nx_market'
	return A,False,False,None
def inc_market(inc):
	A=inc
	if A=='GB':return'בריטניה'
	if A=='US':return'ארצות הברית'
	if A in EU_MEMBERS:return'האיחוד האירופי'
def market_rows(a):
	A=[]
	for C in a['markets']:
		B=market_row(market_code(C))
		if B and B not in A:A.append(B)
	return A
def geo_markets(a):
	A=market_rows(a);B=inc_market(country_code(a.get('incorporation_country')))
	if B and B not in A:A.append(B)
	return A
def derive(a):
	D=a['display_language'];A=T[D];B,G=[],[];I,F,Y,Z=nexus(a);K=A[Z]if Z else None;L=Y and not F
	if I is None:G.append(A['q_country'])
	Q=re.sub('[\\s\\-.]','',str(a.get('registration_number')or''))
	if Q and(I=='IL'or a['organization_type']in IL_REGISTERED_FORMS)and not il_check_digit(Q):G.append(A['q_regno']%Q)
	l=I not in(None,'IL')or any(market_code(A)not in('IL',)for A in a['markets'])
	if l and not(a.get('organization_name_en')or'').strip()and re.search('[\\u0590-\\u05ff]',a.get('organization_name')or''):G.append(A['q_name_en'])
	if F:
		add(B,'הרשות להגנת הפרטיות','Confirmed',A['privacy']%K);add(B,'רשות התחרות','Potential',A['il_axis']%K)
		for M in['רשות המסים','רשם החברות, רשות התאגידים','משרד העבודה, מינהל הסדרה ואכיפה','המוסד לביטוח לאומי','נציבות שוויון זכויות לאנשים עם מוגבלות']:
			if M=='רשם החברות, רשות התאגידים'and a['organization_type']in NON_COMPANY_FORMS:continue
			add(B,M,'Confirmed',A['il_axis']%K)
	elif L:add(B,'הרשות להגנת הפרטיות','Potential',A['privacy']%K);add(B,'רשות התחרות','Potential',A['il_axis']%K)
	R=label('form',a['organization_type'],D)
	if I=='IL':
		for(C,E,*b)in CORPORATE_REGULATORS.get(a['organization_type'],[]):add(B,C,E,A[b[0]if b else'corp']%R)
	for(m,H,S,C)in FOREIGN_FORM_REGULATORS:
		if a['organization_type']not in m:continue
		if I==H:add(B,C,'Likely',A['corp_inc']%(R,label('market',S,D)))
		elif S in market_rows(a):add(B,C,'Potential',A['corp_mkt']%(R,label('market',S,D)))
	N=sorted(((A,venue_code(A))for A in a['listed_in']),key=lambda x:x[1]!='DUAL')
	if a['organization_type'].startswith('חברת אג״ח')and(any(A=='TASE'for(B,A)in N)or not N and(F or L)):add(B,'רשות ניירות ערך','Confirmed'if F or N else'Potential',A['bond'])
	for(n,H)in N:
		if H=='DUAL':
			add(B,'רשות ניירות ערך','Confirmed',A['dual'])
			if not a['dual_listed_in']:G.append(A['q_dual'])
			for c in a['dual_listed_in']:
				for(C,E)in VENUE_REGULATORS.get(venue_code(c),[]):add(B,C,E,A['dual_on']%label('dual',c,D))
			continue
		for(C,E)in VENUE_REGULATORS.get(H,[]):add(B,C,E,A['listed_on']%label('listed',n,D))
	for J in a['financial_activity']:
		U=label('fin',J,D)
		if not F and not L:G.append(A['q_fin']%U);continue
		V='Confirmed'if F else'Potential';O=A['fin']%U if F else A['fin_mkt']%U
		if J in SEC_ISA:add(B,'רשות ניירות ערך',V,O)
		if J in CMISA:add(B,'רשות שוק ההון, ביטוח וחיסכון',V,O)
		if J in BOI:add(B,'בנק ישראל, הפיקוח על הבנקים',V,O)
		if J in FIN_POTENTIAL:add(B,FIN_POTENTIAL[J],'Potential',O)
	for d in a['sectors']:
		for C in SECTOR_REGULATORS.get(d,[]):
			if C in SECTOR_IL_MARKET_ONLY and not Y:continue
			if C not in SECTOR_NOT_IL and not F and not L:continue
			E='Potential'if L and C not in SECTOR_NOT_IL else'Likely';add(B,C,E,A['sector']%label('sector',d,D))
	for W in a['markets']:
		H=market_code(W);e=market_row(H)
		if e:
			for(C,E)in MARKET_REGULATORS.get(e,[]):add(B,C,E,A['market']%label('market',W,D))
		elif H!='IL':G.append(A['q_market']%label('market',W,D))
	f=inc_market(I)
	if f:
		o=label('country',(a.get('incorporation_country')or'').strip(),D)
		for(C,E)in MARKET_REGULATORS.get(f,[]):add(B,C,'Likely'if E=='Potential'else E,A['geo_inc']%o)
	def X(n):n=str(n).strip();return REG_HE.get(n.casefold(),n)
	g=set(X(A)for A in a.get('removed_regulators')or[]);B=[A for A in B if A['regulator_name']not in g];h=[A for A in a.get('user_declared_regulators')or[]if X(A)not in g];i=set(X(A)for A in h);P=[A for A in B if A['regulator_name']in PRIMARY_DISPLAY and A['regulator_name']not in i];j=[A for A in B if A['regulator_name']not in PRIMARY_DISPLAY and A['regulator_name']not in i];P.sort(key=lambda r:PRIMARY_DISPLAY.index(r['regulator_name']))
	for M in h:P.append({'regulator_name':M,'applicability_status':'UserDeclared','basis':A['declared']})
	for k in P+j:k['regulator_name']=reg_label(k['regulator_name'],D)
	return P,j,G
def normalize_answers(a):
	a=dict(a)
	for(A,C)in(('listed_in',[]),('dual_listed_in',[]),('sectors',[]),('financial_activity',[]),('markets',[]),('display_language','he')):
		if a.get(A)in(None,'','-'):a[A]=C
	for A in('listed_in','dual_listed_in','sectors','financial_activity','markets'):
		if isinstance(a[A],str):a[A]=[A.strip()for A in a[A].split(',')if A.strip()and A.strip()!='-']
	a['listed_in']=[A for A in a['listed_in']if str(A).strip().casefold()not in NOT_LISTED];D=str(a.get('display_language')or'he').strip().lower();a['display_language']='en'if D in('en','english','אנגלית')else'he';a['organization_type']=(a.get('organization_type')or'').strip()
	if not a.get('registration_number')and a.get('company_number'):a['registration_number']=a['company_number']
	for(A,B)in FIELD_LABELS.items():
		if isinstance(a.get(A),list):a[A]=[canon(B,A)for A in a[A]]
		elif a.get(A):a[A]=canon(B,a[A])
	return a
COUNSEL_TITLE_RE=re.compile('^\\s*(?:עו(?:"|״|\\x27\\x27|”)ד|עוה(?:"|״)ד|עורך הדין|עורכת הדין|Adv\\.?|Advocate)\\s+',re.I)
def split_signer(raw,role=None):
	A=raw;A=(A or'').strip();E=F=None;B=re.search('\\(([^()]*)\\)\\s*$',A)
	if B and re.search('[A-Za-z]',B.group(1)):C=[A.strip()for A in B.group(1).split(',',1)];E=COUNSEL_TITLE_RE.sub('',C[0]).strip()or None;F=C[1]if len(C)>1 and C[1]else None;A=A[:B.start()].strip()
	D=[A.strip()for A in A.split(',',1)];G=COUNSEL_TITLE_RE.sub('',D[0]).strip()or None;H=D[1]if len(D)>1 and D[1]else None;return G,(role or'').strip()or H,E,F
def signatories_of(a):
	A=a.get('signatories')
	if A in(None,'','-',[]):A=a.get('signatory')
	if A in(None,'','-',[]):
		A=a.get('signer')or a.get('lawyer_name');A=[A for A in re.split('\\s*[;\\n]\\s*',A or'')if A.strip()and A.strip()!='-']
		if len(A)==1 and(a.get('signer_role')or a.get('lawyer_role')):A=[{'name':A[0],'role':a.get('signer_role')or a.get('lawyer_role')}]
	if isinstance(A,(str,dict)):A=[A]
	F=[]
	for B in A or[]:
		if isinstance(B,dict):E,G,C,D=split_signer(B.get('name'),B.get('role'));C,D=B.get('name_en')or C,B.get('role_en')or D
		else:E,G,C,D=split_signer(str(B))
		if E:F.append({'name':E,'role':G,'name_en':C,'role_en':D})
	return F
def logo_state(a):
	A=a.get('logo_path')or None;B=(a.get('logo')or'').strip()
	if A:return'attached',A
	if B in('בלי לוגו','none','no logo','No logo'):return'none',None
	if B:return'later',None
	return'none',None
def build(a):
	for L in('organization_name','organization_type'):
		if not a.get(L):print('חסר שדה חובה בתשובות: %s'%L);sys.exit(2)
	A=a['display_language'];B=T[A];U,V,M=derive(a);G,N=[],{}
	for(W,X)in CATALOG_TRIGGERS:
		if W(a):
			for C in X:
				H=CATALOG_EN.get(C,C)if A=='en'else C
				if H not in G:G.append(H)
				if C in CATALOG_CONDITION_OF:N[H]=CATALOG_CONDITIONS[CATALOG_CONDITION_OF[C]][A]
	D=lambda kind,vs:[label(kind,B,A)for B in vs];I=D('sector',a['sectors']);E=date.today().isoformat();O=(a.get('registration_number')or'').strip();Y=re.sub('[\\s\\-.]','',O)or None;Z,J=logo_state(a);P=normalize_website(a.get('website'));Q=THEME_CHOICES.get(str(a.get('brand_theme')or'').strip());b={'choice':Q,'asked_at':E}if Q and(J or P)else None;K=signatories_of(a);F=K[0]if K else{};R,c,d,e=F.get('name'),F.get('role'),F.get('name_en'),F.get('role_en')
	if not R:M.append(B['q_signer'])
	S={'schema_version':SCHEMA_VERSION,'core_version':CORE_VERSION,'profile_id':'orgprof_'+uuid.uuid4().hex[:12],'version':1,'status':'Provisional','checked_at':E,'confidential':B['confidential'],'organization_name':a['organization_name'],'organization_name_en':(a.get('organization_name_en')or'').strip()or None,'registration_number':O or None,'organization_id':Y,'incorporation_country':country_code(a.get('incorporation_country')),'incorporation_state':parse_country(a.get('incorporation_country'))[1],'incorporation_country_name':label('country',(a.get('incorporation_country')or'').strip(),A)or None,'organization_type':label('form',a['organization_type'],A),'organization_type_basis':B['type_basis'],'public_market':{'listed':bool(a['listed_in']),'venues':D('listed',a['listed_in']),'dual_listed_in':D('dual',a['dual_listed_in'])},'sector':{'primary':I[0]if I else None,'all':I,'financial_activity':D('fin',a['financial_activity']),'description':(a.get('activity_description')or'').strip()or None},'material_operating_jurisdictions':D('market',a['markets']),'regulatory_footprint_primary':U,'regulatory_footprint_secondary':V,'clause_catalog_activated':G,'clause_catalog_conditions':N,'unresolved_questions':M,'removed_regulators':[str(A).strip()for A in a.get('removed_regulators')or[]if str(A).strip()],'onboarding':{'research_performed':False,'method':B['method']},'notes':[B['note']],'branding':{'lawyer_name':R,'lawyer_role':c,'lawyer_name_en':d,'lawyer_role_en':e,'signatories':K,'logo_path':J,'logo_added_at':E if J else None,'logo_status':Z,'website':P,'theme':b},'display_language':a['display_language'],'deliverable_language':a.get('deliverable_language',a['display_language']),'connections':a.get('connections',{'folders':[],'shared_output_folder':a.get('shared_output_folder'),'email':None,'calendar':None,'email_tracking':None,'doc_access':{'mode':'local','baseUrl':''},'asked_at':''}),'areo_notice_shown':True,'generated_at':E,'last_updated':E};S['connections'].setdefault('shared_output_folder',None);return S
def cell(v):return str(v).replace('|','/').replace('\n',' ')
def print_summary(p):
	B=p.get('display_language')if p.get('display_language')in T else'he';A=T[B];C=A['missing'];p=dict(p);p.setdefault('public_market',{'venues':[],'dual_listed_in':[]});p['public_market']=dict({'venues':[],'dual_listed_in':[]},**p['public_market']or{});p['sector']=dict({'all':[],'financial_activity':[],'description':None},**p.get('sector')or{});p['branding']=dict({'lawyer_name':None,'logo_status':'none'},**p.get('branding')or{})
	if p['branding'].get('logo_status')not in LOGO_LABELS[B]:p['branding']['logo_status']='attached'if p['branding'].get('logo_path')else'none'
	for F in('incorporation_country_name','organization_name_en','organization_type'):p.setdefault(F,None)
	p.setdefault('material_operating_jurisdictions',[]);p.setdefault('regulatory_footprint_primary',[]);p['display_language']=B;K=p.get('registration_number')or p.get('organization_id')or C;E=', '.join(A for A in p['public_market']['venues']if venue_code(A)!='DUAL');I=p['public_market']['dual_listed_in']
	if any(venue_code(A)=='DUAL'for A in p['public_market']['venues']):E=(E+', 'if E else'')+label('listed','רישום דואלי',B)+(' (%s)'%', '.join(I)if I else'')
	J=', '.join(p['sector']['all'])or C
	if p['sector']['financial_activity']:J+=' (%s)'%', '.join(p['sector']['financial_activity'])
	D=[(A['r_name'],A['v_name']%(p['organization_name'],K)),(A['r_name_en'],p.get('organization_name_en')or A['v_name_en_none']),(A['r_country'],p['incorporation_country_name']or C),(A['r_form'],p['organization_type']or C),(A['r_listed'],E or A['not_listed']),(A['r_sectors'],J)]
	if p['sector']['description']:D.append((A['r_desc'],p['sector']['description']))
	G=p['branding'].get('signatories')or([{'name':p['branding']['lawyer_name'],'role':p['branding'].get('lawyer_role')}]if p['branding']['lawyer_name']else[])
	if B=='en':G=[dict(A,name=A.get('name_en')or A.get('name'),role=A.get('role_en')or A.get('role'))for A in G]
	D+=[(A['r_markets'],', '.join(p['material_operating_jurisdictions'])or C),(A['r_signer'],'; '.join(A['name']+(', '+A['role']if A.get('role')else'')for A in G)or C),(A['r_lang'],A['v_lang'][p['display_language']]),(A['r_logo'],LOGO_LABELS[B][p['branding']['logo_status']])]
	if p['branding'].get('website'):D.append((A['r_site'],p['branding']['website']))
	if(p['branding'].get('theme')or{}).get('choice'):D.append((A['r_brand'],A['v_yesno'][p['branding']['theme']['choice']]))
	print(A['title']);print('');print(A['head']);print('|---|---|')
	for(F,L)in D:print('| %s | %s |'%(F,cell(L)))
	print('');print(A['regs']);print('');print(A['regs_head']);print('|---|---|---|')
	for H in p['regulatory_footprint_primary']:print('| %s | %s | %s |'%(cell(H['regulator_name']),STATUS_LABELS[B][H['applicability_status']],cell(H['basis'])))
	if not p['regulatory_footprint_primary']:print(A['no_regs'])
	if p.get('unresolved_questions'):
		print('');print(A['q_title']);print('')
		for M in p['unresolved_questions']:print('- '+M)
def entity_dirname(name):return re.sub('[<>:"/\\\\|?*\\x00-\\x1f]','',name).strip().rstrip('.')or'ישות'
def write_json(path,obj):
	A=path;B=os.path.dirname(os.path.abspath(A))
	if B and not os.path.isdir(B):os.makedirs(B)
	io.open(A,'w',encoding='utf-8').write(json.dumps(obj,ensure_ascii=False,indent=2));json.load(io.open(A,encoding='utf-8'))
def report(p,path):
	B=T[p.get('display_language')if p.get('display_language')in T else'he'];print(B['saved']+' '+path);A=p.get('display_language')=='en';print(('Primary regulators shown: %d. Other regulators, stored and not shown: %d'if A else'רגולטורים עיקריים, לתצוגה: %d. רגולטורים נוספים, נשמרים ואינם מוצגים: %d')%(len(p['regulatory_footprint_primary']),len(p['regulatory_footprint_secondary'])))
	if p['clause_catalog_activated']:print(('Clause topics activated: 'if A else'סעיפי קטלוג שהופעלו: ')+', '.join(p['clause_catalog_activated']))
	for(C,D)in(p.get('clause_catalog_conditions')or{}).items():print(('Conditional clause topic: %s. %s'if A else'סעיף קטלוג מותנה: %s. %s')%(C,D))
	for E in p['unresolved_questions']:print(B['openq']%E)
SET_PROTECTED='profile_id','schema_version','core_version','generated_at','checked_at','version'
SET_NEW_OK='organization_name_en','branding.signatories','branding.policy_approver','deliverable_language','deliverable_language_basis','departments_involved','departments_involved.asked_at','branding.website','branding.theme','branding.lawyer_name_en','branding.lawyer_role_en'
SET_FAMILY_FIELD='departments_involved'
DELIVERABLE_LANGS='he','en','both'
SET_ALLOWED='organization_name_en','registration_number','branding.signatories','branding.policy_approver','branding.lawyer_name','branding.lawyer_role','branding.lawyer_name_en','branding.lawyer_role_en','branding.logo_path','branding.logo_status','branding.logo_added_at','branding.website','branding.theme','deliverable_language','deliverable_language_basis'
SET_ALLOWED_PREFIXES=SET_FAMILY_FIELD,'connections'
SET_REBUILD='display_language',
SET_REFUSED='connections.case_law_connector',
LOGO_STATUSES='attached','later','none'
LOCAL_PATH_FIELDS='connections.shared_output_folder','connections.folders','connections.doc_access.baseUrl','branding.logo_path'
def set_allowed(key):
	A=key
	if A in SET_REBUILD:return True
	if A in SET_REFUSED:return False
	return A in SET_ALLOWED or any(A==B or A.startswith(B+'.')for B in SET_ALLOWED_PREFIXES)
PUBLIC_FIELDS='schema_version','core_version','profile_id','version','status','checked_at','organization_name','organization_name_en','registration_number','organization_id','incorporation_country','incorporation_state','incorporation_country_name','organization_type','organization_type_basis','public_market','sector','material_operating_jurisdictions','regulatory_footprint_primary','regulatory_footprint_secondary','branding.website','branding.theme','display_language','deliverable_language','generated_at','last_updated'
def public_profile(prof):
	import copy;D={}
	for F in PUBLIC_FIELDS:
		B=F.split('.');A,C=prof,D
		for E in B[:-1]:
			A=A.get(E)if isinstance(A,dict)else None
			if not isinstance(A,dict):break
			C=C.setdefault(E,{})
		else:
			if isinstance(A,dict)and B[-1]in A:C[B[-1]]=copy.deepcopy(A[B[-1]])
	return D
def areo_copy(path,to=None):
	A=path
	if not os.path.isfile(A):print('אין פרופיל בנתיב %s'%A);return 2
	B=public_profile(json.load(io.open(A,encoding='utf-8')))
	if to:write_json(to,B);print(('The copy for Areo was written: %s'if B.get('display_language')=='en'else'העותק ל-Areo נכתב: %s')%to)
	else:print(json.dumps(B,ensure_ascii=False,indent=2))
	return 0
ROLE_WORDS='היועץ','היועצת','המשפטי','המשפטית','מנכ"ל','מנכ״ל','סמנכ"ל','הלשכה','המחלקה','general counsel','legal counsel','ceo'
def is_person_name(name):A=' '.join(str(name or'').split());return len(A.split())>=2 and not any(B.lower()in A.lower()for B in ROLE_WORDS)
def check_set_value(key,val):
	B=key;A=val
	if B=='branding.policy_approver':
		if A is None:return None,None
		if not isinstance(A,dict)or not is_person_name(A.get('name')):return None,'branding.policy_approver: {"name": "<שם פרטי ומשפחה>", "role": "<תפקיד>"}, שם אדם מלא'
		return{'name':' '.join(A['name'].split()),'role':' '.join(str(A.get('role')or'').split())or None},None
	if B=='branding.website':
		F=normalize_website(A)
		if A not in(None,'')and not F:return None,'branding.website: כתובת אתר, למשל example.co.il או https://www.example.com'
		return F,None
	if B=='branding.theme':
		if not isinstance(A,dict)or THEME_CHOICES.get(str(A.get('choice')or''))is None:return None,'branding.theme: {"choice": "yes|no", "asked_at": "YYYY-MM-DD"}'
		if not re.match('^\\d{4}-\\d{2}-\\d{2}$',str(A.get('asked_at')or'')):return None,'branding.theme.asked_at בפורמט YYYY-MM-DD'
		return{'choice':THEME_CHOICES[str(A['choice'])],'asked_at':A['asked_at']},None
	if B=='branding.logo_status':
		if A not in LOGO_STATUSES:return None,'branding.logo_status מקבל רק attached, later או none'
		return A,None
	if B=='branding.logo_added_at':
		if A is not None and not re.match('^\\d{4}-\\d{2}-\\d{2}$',str(A)):return None,'branding.logo_added_at בפורמט YYYY-MM-DD'
		return A,None
	if B=='display_language':
		if A not in('he','en'):return None,'display_language מקבל רק he או en (display_language accepts only he or en)'
		return A,None
	if B=='deliverable_language':
		if A not in DELIVERABLE_LANGS:return None,'deliverable_language מקבל רק he, en או both'
		return A,None
	if B=='deliverable_language_basis':
		if not isinstance(A,str)or not A:return None,'deliverable_language_basis הוא מחרוזת לא ריקה (למשל user_answer YYYY-MM-DD corpus=he)'
		return A,None
	if B==SET_FAMILY_FIELD:
		if not isinstance(A,dict)or not A:return None,'departments_involved כולו הוא אובייקט JSON: {"<משפחה>": ["<מחלקה>"], "asked_at": "YYYY-MM-DD"}'
		G={}
		for(H,C)in A.items():
			C=C.strip()or None if isinstance(C,str)else C;K,I=check_set_value('%s.%s'%(SET_FAMILY_FIELD,str(H).strip()),C)
			if I:return None,I
			G[str(H).strip()]=K
		return G,None
	if B.startswith(SET_FAMILY_FIELD+'.'):
		D=B[len(SET_FAMILY_FIELD)+1:]
		if not D or'.'in D:return None,'departments_involved.<משפחת ההסכמים>: שם משפחה אחד, בלי נקודה'
		if D=='asked_at':
			if not isinstance(A,str)or not re.match('^\\d{4}-\\d{2}-\\d{2}$',A):return None,'departments_involved.asked_at בפורמט YYYY-MM-DD'
			return A,None
		if not isinstance(A,list)or not A or not all(isinstance(A,str)and A.strip()for A in A):return None,'departments_involved.%s הוא רשימת JSON של שמות מחלקות, למשל \'["משפטית", "כספים"]\''%D
		E=[]
		for J in A:
			if J.strip()not in E:E.append(J.strip())
		return E,None
	return A,None
def set_fields(path,assignments,preview=False):
	I=preview;F=path
	if not os.path.exists(F):print('אין פרופיל בנתיב %s. --set מעדכן פרופיל קיים; פרופיל חדש נבנה מ---answers'%F);return 2
	C=json.load(io.open(F,encoding='utf-8'));J=[];G=None
	for K in assignments:
		A,P,L=K.partition('=');A=A.strip()
		if not P or not A:print('--set %r: נדרש שדה=ערך'%K);return 2
		try:B=json.loads(L)
		except ValueError:B=L
		if isinstance(B,str):B=B.strip()or None
		E=A.split('.')
		if E[0]in SET_PROTECTED:print('השדה %s אינו משתנה ב---set (זהות הפרופיל ותאריך היצירה)'%E[0]);return 2
		if not set_allowed(A):print('השדה %s אינו מתעדכן ב---set. --set משנה רק את תשובות המשתמש על הארגון שהכללים המשותפים (1.7) מתירים: %s, departments_involved.<משפחה>, connections.<הגדרה>. שינוי שמשפיע על גזירת הרגולטורים או על זהות הארגון עובר בעדכון פרופיל, מקובץ תשובות'%(A,', '.join(SET_ALLOWED)));return 2
		M=E[0]==SET_FAMILY_FIELD and len(E)==2;B,N=check_set_value(A,B)
		if N:print(N);return 2
		if A in SET_REBUILD:G=B;continue
		if M and C.get(SET_FAMILY_FIELD)is None:C[SET_FAMILY_FIELD]={}
		D=C
		for O in E[:-1]:
			if not isinstance(D.get(O),dict):print('אין בפרופיל שדה %s'%A);return 2
			D=D[O]
		if E[-1]not in D and A not in SET_NEW_OK and not M:print('אין בפרופיל שדה %s. --set משנה שדה קיים; שדה חדש נכנס בבנייה מ---answers'%A);return 2
		if A==SET_FAMILY_FIELD and isinstance(D.get(A),dict):B=dict(D[A],**B)
		if A=='branding.theme'and isinstance(D.get('theme'),dict)and B['choice']=='yes':B=dict(D['theme'],**B)
		if A=='branding.signatories':B=signatories_of({'signatories':B}if isinstance(B,(list,dict))else{'signer':B or''})
		J.append((A,D.get(E[-1]),B));D[E[-1]]=B
		if A=='registration_number':C['organization_id']=re.sub('[\\s\\-.]','',B or'')or None
	H=T[G or(C.get('display_language')if C.get('display_language')in T else'he')]
	for(A,Q,R)in J:print(set_line(H,A,Q,R))
	if G and G!=C.get('display_language'):
		print(set_line(H,'display_language',C.get('display_language'),G))
		if not I and J:C['last_updated']=date.today().isoformat();write_json(F,C)
		if I and J:print(H['pv']);return 0
		return update_profile(F,{'display_language':G},preview=I)[0]
	if I:print(H['pv']);return 0
	C['last_updated']=date.today().isoformat();write_json(F,C);print(H['upd']);return 0
def set_line(t,key,old,new):
	A=key
	def B(v):
		if v in(None,'',[],{}):return t['none']
		if isinstance(v,str)and v in t['langs']:return t['langs'][v]
		if isinstance(v,list):return', '.join(A.get('name')or''if isinstance(A,dict)else str(A)for A in v)
		if isinstance(v,dict):return', '.join('%s'%(', '.join(A)if isinstance(A,list)else A)for(B,A)in v.items()if B not in('asked_at',)and not isinstance(A,dict))or t['none']
		return str(v)
	C=t['fields'].get(A)or t['fields'].get(A.split('.')[0])or A
	if old in(None,'',[],{}):return t['set_new']%(C,B(new))
	return t['set_line']%(C,B(new),B(old))
THEME_CHOICES={'כן':'yes','yes':'yes','Yes':'yes','לא':'no','no':'no','No':'no'}
LIGHT_BG=255,255,255
DARK_BG=21,25,35
SITE_MAX_BYTES=2097152
SITE_MAX_SHEETS=4
HEX_RE=re.compile('#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\\b')
RGB_RE=re.compile('rgba?\\(\\s*(\\d{1,3})\\s*,\\s*(\\d{1,3})\\s*,\\s*(\\d{1,3})\\s*(?:,\\s*([\\d.]+)\\s*)?\\)')
THEME_TEXT={'he':{'line':'צבעי המותג: ראשי %s, משני %s (מקור: %s)','src':{'user':'הצבעים שמסרתם','logo':'הלוגו','website':'אתר החברה'},'none':'לא נמצאו צבעי מותג בלוגו או באתר. אפשר למסור אותם (למשל #1B4F9C, #F2A900), או להמשיך בעיצוב הרגיל של Areo.','consent':'הלקוח לא אישר מיתוג (branding.theme.choice אינו yes). שאלו אותו קודם, ורשמו את התשובה ב---set.'},'en':{'line':'Brand colours: primary %s, secondary %s (source: %s)','src':{'user':'the colours you gave','logo':'the logo','website':'the company website'},'none':'No brand colours were found in the logo or on the website. You can give them (for example #1B4F9C, #F2A900), or continue with the standard Areo design.','consent':'The client has not approved branding (branding.theme.choice is not yes). Ask first, and record the answer with --set.'}}
def normalize_website(v):
	v=v.strip()if isinstance(v,str)else''
	if not v or v=='-':return
	if not re.match('^https?://',v,re.I):v='https://'+v
	A=re.sub('^https?://','',v,flags=re.I).split('/')[0].split(':')[0].lower()
	if not re.match('^[a-z0-9\\-]+(\\.[a-z0-9\\-]+)+$',A):return
	return v
def _hex(c):return'#%02X%02X%02X'%tuple(max(0,min(255,int(round(A))))for A in c)
def _rgb(h):
	h=h.lstrip('#')
	if len(h)==3:h=''.join(A*2 for A in h)
	return tuple(int(h[A:A+2],16)for A in(0,2,4))
def _lum(c):
	def A(x):x=x/255.;return x/12.92 if x<=.03928 else((x+.055)/1.055)**2.4
	B,C,D=(A(B)for B in c);return .2126*B+.7152*C+.0722*D
def _contrast(a,b):A,B=sorted((_lum(a),_lum(b)),reverse=True);return(A+.05)/(B+.05)
def _hls(c):import colorsys as A;return A.rgb_to_hls(*(A/255. for A in c))
def _from_hls(h,l,s):import colorsys as A;return tuple(A*255 for A in A.hls_to_rgb(h,max(.0,min(1.,l)),s))
def _fit(c,bg,ratio,darker):
	B=darker;D,A,E=_hls(c);F=-.02 if B else .02
	for G in range(60):
		C=_from_hls(D,A,E)
		if _contrast(C,bg)>=ratio:return C
		A+=F
		if A<=0 or A>=1:break
	return(0,0,0)if B else(255,255,255)
def _mix(a,b,t):return tuple(A*(1-t)+B*t for(A,B)in zip(a,b))
def _best_ink(c,inks):return max(inks,key=lambda k:_contrast(c,k))
def _count(counter,rgb,w=1):A=counter;B=tuple(int(A)//16 for A in rgb);C,D=A.get(B,(0,(0,0,0)));A[B]=C+w,tuple(A+B*w for(A,B)in zip(D,rgb))
def colors_from_css(text,counter,weight=1):
	E=weight;D=counter;C=text
	for A in re.finditer('<meta[^>]+name=[\\"\']theme-color[\\"\'][^>]*>',C,re.I):
		B=HEX_RE.search(A.group(0))
		if B:_count(D,_rgb(B.group(0)),40*E)
	for A in re.finditer('--[\\w-]*(?:brand|primary|accent|main|theme)[\\w-]*\\s*:\\s*([^;}]+)',C,re.I):
		B=HEX_RE.search(A.group(1))
		if B:_count(D,_rgb(B.group(0)),15*E)
	for A in HEX_RE.finditer(C):_count(D,_rgb(A.group(0)),E)
	for A in RGB_RE.finditer(C):
		if A.group(4)is None or float(A.group(4))>=.5:_count(D,tuple(min(255,int(A.group(B)))for B in(1,2,3)),E)
def _png_pixels(raw,limit=40000):
	H=raw
	if not H.startswith(b'\x89PNG\r\n\x1a\n'):return
	D,W,O,P,F=8,[],None,None,None
	while D+8<=len(H):
		X=int.from_bytes(H[D:D+4],'big');I,E=H[D+4:D+8],H[D+8:D+8+X];D+=12+X
		if I==b'IHDR':F=E
		elif I==b'PLTE':O=E
		elif I==b'tRNS':P=E
		elif I==b'IDAT':W.append(E)
		elif I==b'IEND':break
	if not F:return
	J,Y=int.from_bytes(F[0:4],'big'),int.from_bytes(F[4:8],'big');e,Q,f=F[8],F[9],F[12];C={2:3,6:4,3:1}.get(Q)
	if e!=8 or f or not C or Q==3 and not O:return
	try:E=zlib.decompress(b''.join(W))
	except zlib.error:return
	Z,T,R,K=J*C,bytearray(J*C),[],0;g=max(1,J*Y//limit)
	for h in range(Y):
		if K>=len(E):break
		S,A=E[K],bytearray(E[K+1:K+1+Z]);K+=1+Z
		for B in range(len(A)):
			L=A[B-C]if B>=C else 0;M=T[B];U=T[B-C]if B>=C else 0
			if S==1:A[B]=A[B]+L&255
			elif S==2:A[B]=A[B]+M&255
			elif S==3:A[B]=A[B]+(L+M>>1)&255
			elif S==4:V=L+M-U;a,b,c=abs(V-L),abs(V-M),abs(V-U);A[B]=A[B]+(L if a<=b and a<=c else M if b<=c else U)&255
		T=A
		for d in range(J):
			if(h*J+d)%g:continue
			G=d*C
			if G+C>len(A):break
			if Q==3:
				N=A[G]
				if N*3+3>len(O)or P and N<len(P)and P[N]<128:continue
				R.append(tuple(O[N*3:N*3+3]))
			elif Q==6:
				if A[G+3]>=128:R.append(tuple(A[G:G+3]))
			else:R.append(tuple(A[G:G+3]))
	return R
def colors_from_logo(path,counter):
	C=counter
	try:A=io.open(path,'rb').read()
	except OSError:return False
	if path.lower().endswith('.svg')or b'<svg'in A[:2048].lower():colors_from_css(A.decode('utf-8','replace'),C);return True
	B=_png_pixels(A)
	if B is None:
		try:from PIL import Image;D=Image.open(io.BytesIO(A)).convert('RGBA');D.thumbnail((160,160));B=[A[:3]for A in D.getdata()if A[3]>=128]
		except Exception:return False
	for E in B:_count(C,E)
	return True
def fetch_site(url):
	A=url;import urllib.request;from urllib.parse import urljoin as J,urlsplit as B;C=(B(A).hostname or'').lower();D=C[4:]if C.startswith('www.')else C
	def E(u):A=(B(u).hostname or'').lower();return B(u).scheme in('http','https')and(A==D or A.endswith('.'+D))
	def F(u):
		u=u.split('#')[0].split('?')[0]
		if not E(u):return''
		B=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0 (compatible; AreoBrand/1.0)'})
		with urllib.request.urlopen(B,timeout=12)as A:
			if not E(A.geturl()):return''
			return A.read(SITE_MAX_BYTES).decode('utf-8','replace')
	G=F(A);H=[G]
	for K in re.findall('<link[^>]+rel=[\\"\']?stylesheet[\\"\']?[^>]*>',G,re.I)[:SITE_MAX_SHEETS]:
		I=re.search('href=[\\"\']([^\\"\']+)[\\"\']',K)
		if I:
			try:H.append(F(J(A,I.group(1))))
			except Exception:pass
	return H
def pick_palette(counter):
	A=[]
	for(D,H)in counter.values():E=tuple(A/D for A in H);I,J,K=_hls(E);A.append((D,E,I,J,K))
	A.sort(key=lambda x:-x[0]);C=[A for A in A if A[4]>=.22 and .12<=A[3]<=.9]
	if C:B=C[0];F=next((A for A in C[1:]if min(abs(A[2]-B[2]),1-abs(A[2]-B[2]))>=25/36e1 and A[0]>=B[0]*.04),None);return B[1],F[1]if F else None
	G=[A for A in A if A[3]<.45];return(G[0][1],None)if G else(None,None)
def theme_tokens(primary,accent=None):A=primary;D=accent or A;B=_fit(A,LIGHT_BG,4.5,darker=True);E=_fit(D,LIGHT_BG,3.,darker=True);C=_fit(A,DARK_BG,4.5,darker=False);F=_fit(D,DARK_BG,3.,darker=False);return{'primary_light':_hex(B),'secondary_light':_hex(E),'soft_light':_hex(_mix(B,LIGHT_BG,.9)),'on_light':_hex(_best_ink(B,((255,255,255),(16,34,28)))),'primary_dark':_hex(C),'secondary_dark':_hex(F),'soft_dark':_hex(_mix(C,DARK_BG,.86)),'on_dark':_hex(_best_ink(C,((14,16,22),(255,255,255))))}
def derive_theme(path,colors=None,site_files=(),fetch=False,preview=False):
	Q=fetch;P=colors;K=site_files;C=path
	if not os.path.isfile(C):print('אין פרופיל בנתיב %s'%C);return 2
	F=json.load(io.open(C,encoding='utf-8'));I=THEME_TEXT['en'if F.get('display_language')=='en'else'he'];B=F.setdefault('branding',{});R=B.get('theme')or{}
	if R.get('choice')!='yes':print(I['consent']);return 2
	A=D=G=None
	if P:
		J=[_rgb(A.group(0))for A in HEX_RE.finditer(P)]
		if not J:print('--colors: צבע אחד או שניים בפורמט #RRGGBB');return 2
		A,D,G=J[0],J[1]if len(J)>1 else None,'user'
	if A is None and B.get('logo_path'):
		E=B['logo_path']
		if not os.path.isabs(E):L=os.path.dirname(os.path.abspath(C));S=[os.path.join(os.path.dirname(L),E),os.path.join(L,E),os.path.join(L,os.path.basename(E))];E=next((A for A in S if os.path.isfile(A)),S[0])
		H={}
		if colors_from_logo(E,H):A,D=pick_palette(H);G='logo'if A is not None else None
	if A is None and(K or Q and B.get('website')):
		H,M={},[]
		for T in K:M.append(io.open(T,encoding='utf-8',errors='replace').read())
		if Q and B.get('website')and not K:
			try:M=fetch_site(B['website'])
			except Exception as U:print('אתר החברה לא נקרא (%s)'%U)
		for V in M:colors_from_css(V,H)
		A,D=pick_palette(H);G='website'if A is not None else None
	if A is None:print(I['none']);return 3
	N=theme_tokens(A,D);O=dict(R,source=G,primary=_hex(A),accent=_hex(D)if D else None,tokens=N,derived_at=date.today().isoformat());print(I['line']%(O['primary'],O['accent']or N['secondary_light'],I['src'][G]));print(json.dumps(N,ensure_ascii=False))
	if preview:print('תצוגה מקדימה: הפרופיל לא נכתב');return 0
	B['theme']=O;F['last_updated']=date.today().isoformat();write_json(C,F);print(('The profile was updated: %s'if F.get('display_language')=='en'else'הפרופיל עודכן: %s')%C);return 0
REGISTRY='ישויות.json'
def registry_entry(p,rel):return{'name':p['organization_name'],'registration_number':p.get('registration_number')or p.get('organization_id'),'incorporation_country':p.get('incorporation_country'),'profile_id':p.get('profile_id'),'profile_path':rel}
def load_setup(root,flat_path):
	C=flat_path;B=root;G=os.path.join(B,REGISTRY)
	if os.path.exists(G):
		D=json.load(io.open(G,encoding='utf-8'));E=D.get('entities')or[];F=next((A for A in E if A.get('name')==D.get('default_entity')),None)or(E[0]if E else None);A=None
		if F and F.get('profile_path'):
			H=os.path.join(B,*F['profile_path'].split('/'))
			if os.path.exists(H):A=json.load(io.open(H,encoding='utf-8'))
		return D,A
	if not os.path.exists(C):return None,None
	A=json.load(io.open(C,encoding='utf-8'));I=date.today().isoformat();J=os.path.relpath(os.path.abspath(C),B).replace(os.sep,'/');return{'schema_version':SCHEMA_VERSION,'default_entity':A['organization_name'],'entities':[registry_entry(A,J)],'generated_at':I,'last_updated':I},A
def profile_to_answers(p,for_update=False):
	A=p.get('branding')or{};C=p.get('public_market')or{};B=p.get('sector')or{};E=A.get('signatories')or([{'name':A['lawyer_name'],'role':A.get('lawyer_role'),'name_en':A.get('lawyer_name_en'),'role_en':A.get('lawyer_role_en')}]if A.get('lawyer_name')else[]);D={'incorporation_country':p.get('incorporation_country_name')or p.get('incorporation_country')or'','organization_type':p.get('organization_type')or'','listed_in':list(C.get('venues')or[]),'dual_listed_in':list(C.get('dual_listed_in')or[]),'sectors':list(B.get('all')or[]),'financial_activity':list(B.get('financial_activity')or[]),'markets':list(p.get('material_operating_jurisdictions')or[]),'display_language':p.get('display_language')or'he','deliverable_language':p.get('deliverable_language')or p.get('display_language')or'he','signatories':E,'shared_output_folder':(p.get('connections')or{}).get('shared_output_folder')}
	if for_update:D.update({'organization_name':p.get('organization_name')or'','organization_name_en':p.get('organization_name_en')or'','registration_number':p.get('registration_number')or p.get('organization_id')or'','activity_description':B.get('description')or'','logo_path':A.get('logo_path')or'','logo':{'attached':'אעלה עכשיו','later':'אוסיף מאוחר יותר'}.get(A.get('logo_status'),'בלי לוגו'),'website':A.get('website')or'','brand_theme':(A.get('theme')or{}).get('choice')or'','user_declared_regulators':[A.get('regulator_name')for A in p.get('regulatory_footprint_primary')or[]if A.get('applicability_status')=='UserDeclared'],'removed_regulators':list(p.get('removed_regulators')or[]),'connections':p.get('connections')})
	return D
KEEP_ON_UPDATE='departments_involved','deliverable_language','deliverable_language_basis'
FACT_KEYS='incorporation_country','organization_type','listed_in','dual_listed_in','sectors','financial_activity','markets'
STATUS_ORDER={'Confirmed':0,'Likely':1,'Potential':2,'UserDeclared':3}
def facts_of(a):
	D=normalize_answers(a);C={}
	for A in FACT_KEYS:
		B=D.get(A)
		if A=='incorporation_country':C[A]=parse_country(B)if B else(None,None)
		elif A=='markets':C[A]=sorted(str(market_code(A)or A).casefold()for A in B or[])
		elif isinstance(B,list):C[A]=sorted(str(A)for A in B)
		else:C[A]=str(B or'').strip()
	return C
def facts_only_added(of,nf):
	for A in FACT_KEYS:
		if isinstance(of[A],list):
			if not set(of[A])<=set(nf[A]):return False
		elif of[A]!=nf[A]:return False
	return True
def _canon_reg(name):A=str(name or'').strip();return REG_HE.get(A.casefold(),A)
def keep_statuses(old,out):
	E=old;A=out;I=A.get('display_language')if A.get('display_language')in T else'he';M=E.get('display_language')==A.get('display_language');N={_canon_reg(A)for A in A.get('removed_regulators')or[]};F,G=list(A.get('regulatory_footprint_primary')or[]),list(A.get('regulatory_footprint_secondary')or[]);J={_canon_reg(A['regulator_name']):A for A in F+G}
	for H in(E.get('regulatory_footprint_primary')or[])+(E.get('regulatory_footprint_secondary')or[]):
		B=H.get('applicability_status');C=_canon_reg(H.get('regulator_name'))
		if B not in STATUS_ORDER or B=='UserDeclared'or C in N:continue
		K=H.get('basis')if M else T[I]['kept'];D=J.get(C)
		if D is None:L={'regulator_name':reg_label(C,I),'applicability_status':B,'basis':K};(F if C in PRIMARY_DISPLAY else G).append(L);J[C]=L
		elif STATUS_ORDER[B]<STATUS_ORDER.get(D.get('applicability_status'),9):D['applicability_status'],D['basis']=B,K
	O=lambda r:(r['applicability_status']=='UserDeclared',PRIMARY_DISPLAY.index(_canon_reg(r['regulator_name']))if _canon_reg(r['regulator_name'])in PRIMARY_DISPLAY else 99);A['regulatory_footprint_primary']=sorted(F,key=O);A['regulatory_footprint_secondary']=G;return A
def reg_changes(old,new):
	E=new;F=E.get('display_language')if E.get('display_language')in T else'he';G,H=T[F],STATUS_LABELS[F];C={_canon_reg(A['regulator_name']):A['applicability_status']for A in old.get('regulatory_footprint_primary')or[]};B={_canon_reg(A['regulator_name']):A['applicability_status']for A in E.get('regulatory_footprint_primary')or[]};D=[]
	for A in list(C)+[A for A in B if A not in C]:
		I=reg_label(A,F)
		if A in C and A in B and C[A]!=B[A]:D.append(G['chg']%(I,H.get(C[A],C[A]),H.get(B[A],B[A])))
		elif A in B and A not in C:D.append(G['chg_add']%(I,H.get(B[A],B[A])))
		elif A in C and A not in B:D.append(G['chg_del']%I)
	return D
def merge_update(old,new,given,old_answers=None,new_answers=None):
	H=new_answers;G=old_answers;C=old;B=dict(new)
	for A in('profile_id','generated_at','checked_at','schema_version'):
		if C.get(A):B[A]=C[A]
	B['version']=int(C.get('version')or 1)+1;B['last_updated']=date.today().isoformat()
	for A in KEEP_ON_UPDATE:
		if A in C and not(A=='deliverable_language'and'deliverable_language'in given):B[A]=C[A]
	for(A,E)in C.items():
		if A not in B:B[A]=E
	F,D=C.get('branding')or{},dict(B.get('branding')or{})
	for(A,E)in F.items():
		if A not in D or D.get(A)in(None,[],'')and E not in(None,[],''):D[A]=E
	if isinstance(F.get('theme'),dict)and(D.get('theme')or{}).get('choice')==F['theme'].get('choice'):D['theme']=F['theme']
	B['branding']=D
	if isinstance(C.get('connections'),dict):B['connections']=dict(C['connections'],**{A:B for(A,B)in(B.get('connections')or{}).items()if A not in C['connections']})
	if G is not None and H is not None and facts_only_added(facts_of(G),facts_of(H)):keep_statuses(C,B)
	return B
def update_registry_entry(path,prof):
	C=prof;D=os.path.dirname(os.path.abspath(path))
	for G in range(3):
		E=os.path.join(D,REGISTRY)
		if os.path.exists(E):
			A=json.load(io.open(E,encoding='utf-8'));F=False
			for B in A.get('entities')or[]:
				if B.get('profile_id')==C.get('profile_id'):
					if A.get('default_entity')==B.get('name'):A['default_entity']=C['organization_name']
					B.update({A:B for(A,B)in registry_entry(C,B.get('profile_path')).items()if A!='profile_path'});F=True
			if F:A['last_updated']=date.today().isoformat();write_json(E,A)
			return
		D=os.path.dirname(D)
def update_profile(path,changes,preview=False):
	B=path
	if not os.path.isfile(B):print('אין פרופיל בנתיב %s. עדכון חל על פרופיל קיים; פרופיל חדש נבנה מ---answers'%B);return 2,None
	D=json.load(io.open(B,encoding='utf-8'));G={A:B for(A,B)in(changes or{}).items()if A!='entities'and B not in(None,'','-')};H=profile_to_answers(D,for_update=True);I=dict(H,**G);J=normalize_answers(I);A=merge_update(D,build(J),G,H,I);C=T[A['display_language']];E=reg_changes(D,A)
	if preview:
		print_summary(A)
		if E:
			print('');print(C['chg_title']);print('')
			for F in E:print('- '+F)
		print('');print(C['pv']);return 0,A
	write_json(B,A);update_registry_entry(B,A);print(C['upd'])
	for F in E:print('- '+F)
	for K in A['unresolved_questions']:print(C['openq']%K)
	return 0,A
def add_entities(root,registry,profiles,dry=False):
	B=registry;F={(A.get('name')or'').strip().casefold()for A in B.get('entities')or[]};E={re.sub('[\\s\\-.]','',A.get('registration_number')or'')for A in B.get('entities')or[]};E.discard('');G=[]
	for A in profiles:
		D='ישויות/%s/פרופיל-לקוח.json'%entity_dirname(A['organization_name']);C=os.path.join(root,*D.split('/'))
		if A['organization_name'].strip().casefold()in F or(A.get('organization_id')or'')in E:print('הישות %s כבר רשומה ב-%s. הוספת ישות אינה מעדכנת ישות קיימת'%(A['organization_name'],REGISTRY));return 2
		if os.path.exists(C):print('כבר קיים פרופיל בנתיב %s. הוספת ישות אינה דורסת פרופיל'%C);return 2
		F.add(A['organization_name'].strip().casefold())
		if A.get('organization_id'):E.add(A['organization_id'])
		G.append((A,D,C))
	if dry:return 0
	for(A,D,C)in G:write_json(C,A);report(A,C);B.setdefault('entities',[]).append(registry_entry(A,D))
	B['last_updated']=date.today().isoformat();H=os.path.join(root,REGISTRY);write_json(H,B);print('מרשם הישויות עודכן: %s (%d ישויות, ברירת מחדל: %s)'%(H,len(B['entities']),B.get('default_entity')));return 0
def main():
	if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
	B=argparse.ArgumentParser();B.add_argument('--answers',help='תשובות השאלון. נדרש בבנייה; לא עם --set');B.add_argument('--out',help='נתיב פרופיל-לקוח.json. נדרש בשמירה, אחרי האישור, ובעדכון שדה (--set)');B.add_argument('--preview',action='store_true',help='תצוגה מקדימה לאישור: מדפיס את טבלאות התקציר ואינו כותב דבר');B.add_argument('--set',action='append',metavar='FIELD=VALUE',help='עדכון שדה בודד בפרופיל קיים (--out), בלי לבנות אותו מחדש: profile_id, התאריכים וכל השאר נשמרים. אפשר כמה פעמים; נתיב בנקודות לשדה פנימי. רק השדות שהכללים המשותפים (1.7) מתירים: organization_name_en, registration_number, branding.signatories, branding.lawyer_*, branding.logo_path/logo_status/logo_added_at, branding.website, branding.theme, deliverable_language (he|en|both), deliverable_language_basis, departments_involved.<משפחה> (רשימת JSON), departments_involved.asked_at (YYYY-MM-DD), connections.<הגדרה>. כל שדה אחר: סירוב, קוד 2');B.add_argument('--update',action='store_true',help='עדכון פרופיל קיים (--out) מקובץ תשובות חלקי או מלא (--answers): השינויים מתמזגים עם התשובות הקיימות, הרגולטורים נגזרים מחדש, profile_id ותאריך היצירה נשמרים, version עולה באחד, וכל שדה שנוסף אחרי ההקמה נשמר. עם --preview: מדפיס את התקציר ואינו כותב');B.add_argument('--summary',action='store_true',help='צפייה בפרופיל שב---out: מדפיס את התקציר (פרטים, רגולטורים ושאלות פתוחות) ואינו כותב דבר');B.add_argument('--areo-copy',action='store_true',help='העותק של הפרופיל שב---out שנשלח ל-Areo: בלי נתיבי התיקיות המקומיים (connections.shared_output_folder, connections.folders, connections.doc_access.baseUrl, branding.logo_path). מודפס כ-JSON, או נכתב ל---to. הפרופיל עצמו אינו משתנה');B.add_argument('--to',help='עם --areo-copy: קובץ שאליו נכתב העותק, בתיקייה זמנית ולא ב-Areo-נתונים');B.add_argument('--derive-theme',action='store_true',help='גזירת צבעי המותג לפרופיל שב---out (branding.theme.tokens), רק כש-branding.theme.choice הוא yes: מ---colors, מהלוגו שבפרופיל, או מאתר החברה (--fetch-site / --site-file)');B.add_argument('--colors',help='עם --derive-theme: צבעי המותג שהמשתמש מסר, ראשי ומשני, למשל "#1B4F9C,#F2A900"');B.add_argument('--fetch-site',action='store_true',help='עם --derive-theme: קריאת דף הבית של branding.website וגיליונות הסגנון שלו מאותו אתר');B.add_argument('--site-file',action='append',default=[],help='עם --derive-theme: עותק של דף הבית או של גיליון סגנון מאתר החברה, כשאין גישה ישירה');B.add_argument('--add-entity',action='store_true',help='הוספת ישות להתקנה קיימת: פרופיל חדש ב-ישויות/<שם>/ ורישום ב-ישויות.json, בלי לגעת בפרופיל הקיים. --out הוא פרופיל-לקוח.json שבשורש Areo-נתונים');B.add_argument('--inherit',action='store_true',help='עם --add-entity: שדה שחסר בתשובות נורש מהישות הקיימת (כמו הקיימת)');A=B.parse_args()
	if A.inherit and not A.add_entity:B.error('--inherit רק עם --add-entity')
	if A.summary:
		if not A.out or A.answers or A.set or A.update:B.error('--summary מציג את הפרופיל שב---out בלבד')
		if not os.path.isfile(A.out):print('אין פרופיל בנתיב %s'%A.out);sys.exit(2)
		print_summary(json.load(io.open(A.out,encoding='utf-8')));sys.exit(0)
	if A.to and not A.areo_copy:B.error('--to רק עם --areo-copy')
	if A.areo_copy:
		if A.answers or A.set or A.derive_theme or A.add_entity or not A.out:B.error('--areo-copy פועל על הפרופיל שב---out בלבד')
		sys.exit(areo_copy(A.out,A.to))
	if A.derive_theme:
		if A.answers or A.set or not A.out:B.error('--derive-theme פועל על הפרופיל שב---out, בלי --answers ובלי --set')
		sys.exit(derive_theme(A.out,colors=A.colors,site_files=A.site_file,fetch=A.fetch_site,preview=A.preview))
	if A.colors or A.fetch_site or A.site_file:B.error('--colors, --fetch-site ו---site-file רק עם --derive-theme')
	if A.set:
		if A.answers or not A.out or A.update:B.error('--set מעדכן את הפרופיל שב---out, בלי --answers ובלי --update')
		sys.exit(set_fields(A.out,A.set,preview=A.preview))
	if A.update:
		if not A.answers or not A.out or A.add_entity:B.error('--update דורש --answers (השינויים) ו---out (הפרופיל הקיים), בלי --add-entity')
		sys.exit(update_profile(A.out,json.load(io.open(A.answers,encoding='utf-8')),preview=A.preview)[0])
	if not A.answers:B.error('נדרש --answers')
	if not A.preview and not A.out:B.error('נדרש --out לשמירה, או --preview לתצוגה מקדימה')
	if A.add_entity and not A.out:B.error('--add-entity דורש --out: פרופיל-לקוח.json שבשורש Areo-נתונים, גם בתצוגה מקדימה')
	N=json.load(io.open(A.answers,encoding='utf-8'));E={A:B for(A,B)in N.items()if A!='entities'};F=None
	if A.add_entity:
		H=os.path.dirname(os.path.abspath(A.out));F,O=load_setup(H,A.out)
		if F is None:print('אין הקמה קיימת ב-%s. ישות ראשונה נבנית בהקמה רגילה, בלי --add-entity'%H);sys.exit(2)
		if A.inherit:
			if O is None:print('לא נמצא הפרופיל של ישות ברירת המחדל, ולכן אין ממה לרשת. הריצו בלי --inherit, עם התשובות המלאות');sys.exit(2)
			L=profile_to_answers(O)
			if not L.get('incorporation_country')and not E.get('incorporation_country'):print('לישות הקיימת אין מדינת התאגדות בפרופיל, ולכן היא אינה עוברת בירושה. שאלו את מדינת ההתאגדות של הישות החדשה והוסיפו אותה לתשובות (incorporation_country)')
			if any(E.get(A)not in(None,'','-',[])for A in('signer','signatory','lawyer_name')):L.pop('signatories')
			E=dict(L,**{B:A for(B,A)in E.items()if A not in(None,'','-',[])})
	G=N.get('entities')or[]
	if len(G)<2:
		if G:E.update(G[0])
		I=[normalize_answers(E)]
	else:
		I,J=[],E
		for M in G:
			if M.get('organization_name')and'organization_name_en'not in M:J={A:B for(A,B)in J.items()if A!='organization_name_en'}
			J=dict(J,**M);I.append(normalize_answers(J))
	C=[build(A)for A in I]
	if A.add_entity and add_entities(H,F,C,dry=True):sys.exit(2)
	if A.preview and not A.add_entity and len(C)==1 and A.out and os.path.isfile(A.out):sys.exit(update_profile(A.out,E if not G else dict(E,**G[0]),preview=True)[0])
	if A.preview:
		for D in C:
			if len(C)>1:print('### %s'%D['organization_name']);print('')
			print_summary(D);print('')
		return
	if A.add_entity:sys.exit(add_entities(H,F,C))
	if len(C)==1:
		if os.path.isfile(A.out):print('קיים פרופיל ב-%s: הוא מתעדכן במקום, עם אותו profile_id'%A.out);sys.exit(update_profile(A.out,E if not G else dict(E,**G[0]))[0])
		write_json(A.out,C[0]);report(C[0],A.out);return
	H=os.path.dirname(os.path.abspath(A.out));F={'schema_version':SCHEMA_VERSION,'default_entity':C[0]['organization_name'],'entities':[],'generated_at':C[0]['generated_at'],'last_updated':C[0]['generated_at']}
	for(P,D)in enumerate(C):
		Q='ישויות/%s/פרופיל-לקוח.json'%entity_dirname(D['organization_name']);K=os.path.join(H,*Q.split('/'))
		if os.path.isfile(K):R=json.load(io.open(K,encoding='utf-8'));D=merge_update(R,D,I[P],profile_to_answers(R,for_update=True),I[P])
		write_json(K,D);report(D,K);F['entities'].append({'name':D['organization_name'],'registration_number':D.get('registration_number')or D.get('organization_id'),'incorporation_country':D['incorporation_country'],'profile_id':D['profile_id'],'profile_path':Q})
	S=os.path.join(H,'ישויות.json');write_json(S,F);print('מרשם הישויות נשמר: %s (%d ישויות, ברירת מחדל: %s)'%(S,len(C),F['default_entity']))
if __name__=='__main__':main()
