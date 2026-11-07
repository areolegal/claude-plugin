<p align="center">
  <img src="assets/areo-contracts.png" alt="Areo Contracts" width="420">
</p>

<div dir="rtl">

# Areo Contracts

**מערכת לניהול חוזים בעברית, שעובדת בתוך Claude. מבית Areo.**

Areo Contracts בונה פלייבוק חוזי מההסכמים של החברה, מנהלת משא ומתן על טיוטות שחזרו מהצד שכנגד בעקוב אחר שינויים, מעריכה את הסיכונים שהסכם יוצר, מנסחת הסכמים ומסמכים נלווים על הנייר של החברה, מתרגמת חוזים בין עברית לאנגלית תוך שמירה על התוקף המשפטי, ומציעה תוסף לניהול מחזור חיי החוזה (מועדים, חידושים והתחייבויות). הכול קורה בתוך Claude, והמסמכים שלכם נשארים בסביבה שלכם.

## התקנה

לפני שמתחילים ודאו שיש לכם: אפליקציית Claude Desktop (בחשבון Claude בתשלום), מפתח רישיון Areo Contracts מהרכישה, וחיבור לאינטרנט. אין צורך בשום התקנה טכנית נוספת.

בתוך Claude התוסף מופיע בשם **AreoLegal**. זה אותו מוצר, Areo Contracts.

### שלב 1 - התקנת התוסף

1. פתחו את אפליקציית Claude ובסרגל הצד בחרו **Customize** ואז **Plugins**.
2. באזור **Personal plugins** לחצו **"+"** ובחרו **Add marketplace**.
3. הדביקו: `areolegal/claude-plugin` ואשרו.
4. מצאו את **AreoLegal** ברשימה ולחצו **Install**.

### שלב 2 - חיבור המנוי (Connector)

1. בהגדרות בחרו **Connectors** ואז **Add custom connector**.
2. שם: `AreoLegal`, וכתובת: `https://areo.co.il/mcp`
3. לחצו **Connect**. ייפתח דף AreoLegal בדפדפן. הזינו את מפתח הרישיון שלכם (`AREO-...`) ולחצו חיבור.

### שלב 3 - הפעלה ראשונה

1. סגרו את האפליקציה לגמרי ופתחו מחדש.
2. פתחו שיחה חדשה וכתבו: **"הפעל את AreoLegal"**.
3. עקבו אחרי ההנחיות, כולל בניית הפרופיל הארגוני שלכם (פעם אחת).

מדריך ההתקנה המלא ופתרון תקלות: [areo.co.il/legal](https://areo.co.il/legal)

## תמיכה

- אתר: [areo.co.il/legal](https://areo.co.il/legal)
- דוא"ל: [support@areo.co.il](mailto:support@areo.co.il)

השימוש כפוף למנוי פעיל ול[תנאי השימוש](https://areo.co.il/legal/terms). ראו [LICENSE](LICENSE).

© Areo. כל הזכויות שמורות.

</div>

---

## English

**Areo Contracts** is a contract management suite for Hebrew-speaking legal teams that works inside Claude. It builds a contract playbook from your company's own agreements, negotiates counterparty drafts with tracked changes, assesses the risks an agreement creates, drafts agreements and related documents on your company's paper, translates contracts between Hebrew and English while preserving their legal effect, and offers a contract lifecycle management add-on for key dates, renewals and obligations. Everything runs inside Claude, and your documents stay in your environment.

### Installation

You need the Claude Desktop app (on a paid Claude plan), an Areo Contracts licence key from your purchase, and an internet connection. Inside Claude the plugin is listed as **AreoLegal**; it is the same product.

1. **Install the plugin.** In Claude open **Customize > Plugins**. Under **Personal plugins** click **"+"**, choose **Add marketplace**, paste `areolegal/claude-plugin` and confirm. Find **AreoLegal** in the list and click **Install**.
2. **Connect your subscription.** In settings open **Connectors > Add custom connector**. Name: `AreoLegal`, URL: `https://areo.co.il/mcp`. Click **Connect**, enter your licence key (`AREO-...`) on the page that opens, and confirm.
3. **First run.** Quit Claude completely and reopen it. Start a new chat and type **"הפעל את AreoLegal"** (activate AreoLegal), then follow the prompts, including a one-time setup of your organisation profile.

In Claude Code, step 1 is one command:

```
/plugin install areolegal --marketplace areolegal/claude-plugin
```

### Support

- Website: [areo.co.il/legal](https://areo.co.il/legal)
- Email: [support@areo.co.il](mailto:support@areo.co.il)

Use requires an active Areo subscription and is subject to the [terms of use](https://areo.co.il/legal/terms). See [LICENSE](LICENSE).

© Areo. All rights reserved.
