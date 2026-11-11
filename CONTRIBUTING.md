<div dir="rtl" lang="ar">

# قواعد العمل المشترك (CONTRIBUTING)

> اقرأوا هذا الملف **مرة واحدة كاملة** قبل أول commit. عشر دقائق الآن توفر علينا ساعات من المشاكل لاحقًا.
> إن لم تفهموا شيئًا فاسألوا في مجموعة الفريق. السؤال ليس عيبًا، والعيب أن نخمّن ونكسر عمل بعضنا.

---

## القواعد الذهبية الخمس

| # | القاعدة | لماذا؟ |
|---|---|---|
| 1 | ❌ **لا نعمل مباشرة على `main`.** لكل مهمة **فرع (branch)** خاص بها | `main` هو النسخة التي تعمل دائمًا. لا نكسرها |
| 2 | ✅ **كل تغيير يدخل `main` عبر Pull Request** يراجعه زميل آخر | عينان أفضل من عين، ونتعلم من كود بعضنا |
| 3 | ❌ **لا نرفع ملف `.env` ولا أي مفتاح سري** | المفتاح المسرَّب يمكن أن يستهلك حصتنا كلها |
| 4 | ✅ **commits صغيرة برسائل واضحة** | يسهل فهم التاريخ والتراجع عند الخطأ |
| 5 | ✅ **كل واحد يعمل باسمه.** لا نرفع عمل غيرنا ولا نستعمل `--force` | التاريخ يجب أن يُظهر بصدق من فعل ماذا |

> **ملاحظة مهمة:** GitHub لا يمنعنا تقنيًا من الرفع المباشر إلى `main` (هذه الحماية مدفوعة). لذلك **اتفاقنا** هو الحماية الوحيدة، فالتزموا به.

---

## 1. الإعداد لأول مرة (مرة واحدة فقط)

### 1.1 ثبّتوا Git

- Linux (Mint أو Ubuntu): `sudo apt install git`
- Windows: ثبّتوا **Git for Windows** (ومعه Git Bash)

### 1.2 عرّفوا أنفسكم لـGit

<div dir="ltr">

```bash
git config --global user.name "Firstname Lastname"
git config --global user.email "the-email-you-use-on-github@example.com"
```

</div>

⚠️ **البريد يجب أن يكون نفسه المسجَّل في حساب GitHub.** وإلا لن يُنسب عملكم إليكم، وسيظهر كأن أحدًا آخر لم يعمل شيئًا.

### 1.3 اربطوا جهازكم بـGitHub

الأسهل لكم أحد طريقين:

**الطريقة أ: مفتاح SSH** (مرة واحدة، ثم لا كلمة سر بعد ذلك)

<div dir="ltr">

```bash
ssh-keygen -t ed25519 -C "the-email-you-use-on-github@example.com"
cat ~/.ssh/id_ed25519.pub
```

</div>

انسخوا ما يطبعه الأمر الثاني، ثم في GitHub: **Settings ← SSH and GPG keys ← New SSH key** وألصقوه. للتأكد:

<div dir="ltr">

```bash
ssh -T git@github.com
```

</div>

**الطريقة ب: VS Code.** سجّلوا الدخول إلى GitHub من داخله (أيقونة الحساب أسفل اليسار)، فيتولى هو الاتصال.

### 1.4 انسخوا المشروع إلى جهازكم (clone)

<div dir="ltr">

```bash
git clone git@github.com:rcr-project1/jurideazor.git
cd jurideazor
```

</div>

(أو من الصفحة الرئيسية للمستودع: زر **Code** الأخضر ← **SSH** ← انسخوا الرابط.)

### 1.5 بيئة بايثون

<div dir="ltr">

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # once the file exists
```

</div>

---

## 2. دورة العمل اليومية (خطوة بخطوة)

هذه هي الدورة التي تتكرر في كل مهمة:

<div dir="ltr">

```bash
# 1) start from the latest main
git switch main
git pull

# 2) create YOUR branch for this task
git switch -c collect/download-script

# 3) work on your files... then check what changed
git status

# 4) choose the files and save a commit
git add src/collect/download.py
git commit -m "collect: add polite PDF downloader"

# 5) send your branch to GitHub
git push -u origin collect/download-script
```

</div>

### ماذا يفعل كل أمر؟

| الأمر | ماذا يفعل (بالعربية) |
|---|---|
| `git switch main` | ينتقل إلى الفرع الرئيسي |
| `git pull` | يجلب آخر ما رفعه الفريق إلى جهازك |
| `git switch -c اسم-الفرع` | **ينشئ فرعًا جديدًا** وينتقل إليه |
| `git status` | يُريك ما تغيّر وما ينتظر الحفظ. **استعملوه كثيرًا** |
| `git add ملف` | يختار الملف ليدخل في الـcommit القادم |
| `git commit -m "رسالة"` | يحفظ لقطة من عملك مع رسالة تشرحها (هذا هو الـcommit) |
| `git push -u origin اسم-الفرع` | يرسل فرعك إلى GitHub (`-u` تُكتب أول مرة فقط، وبعدها `git push` تكفي) |

### أسماء الفروع

الصيغة: `الوحدة/وصف-قصير` بأحرف صغيرة وشرطات بدل المسافات.

✅ `collect/ocr-fallback` ✅ `structure/split-articles` ✅ `search/bm25-baseline`
❌ `my-branch` ❌ `test` ❌ `new2`

### بعد أن ينتهي عملك

1. افتحوا صفحة المستودع في GitHub. سيظهر شريط أصفر **Compare & pull request**، اضغطوه.
2. اتبعوا الفقرة 4 (Pull Request) أدناه.
3. بعد الموافقة والدمج، ارجعوا إلى جهازكم:

<div dir="ltr">

```bash
git switch main
git pull
```

</div>

### إن تأخر فرعك عن `main`

إذا رفع الفريق تغييرات جديدة أثناء عملك، حدّثوا فرعكم قبل فتح الـPull Request:

<div dir="ltr">

```bash
git switch main
git pull
git switch your-branch
git merge main
```

</div>

> 💡 **عادتان تحميكم من أغلب المشاكل:** `git pull` قبل أن تبدأوا، و`git push` قبل أن تناموا (على فرعكم، حتى لو لم ينته العمل، فهذا نسخة احتياطية).

---

## 3. رسائل الـcommit (comments)

رسالة الـcommit هي الجملة التي تشرح **ما فعلتموه**. بعد أسابيع ستقرؤها أنتم والأستاذ، فاجعلوها مفهومة.

### الصيغة

<div dir="ltr">

```text
<module>: <what you did>
```

</div>

- **الوحدة (module)** من هذه القائمة، وأغلبها بحسب مجلدات المشروع:

| الوحدة | متى نستعملها | مثال |
|---|---|---|
| `collect` | جمع الملفات والتحميل وOCR | `collect: add OCR for scanned pages` |
| `structure` | تقطيع النصوص إلى مواد | `structure: split articles with regex` |
| `versions` | نسخ المواد وتواريخها | `versions: close old version on repeal` |
| `search` | محرك البحث | `search: add BM25 baseline` |
| `answer` | الجواب والتحقق والحساب | `answer: verify cited quotes` |
| `app` | الواجهة | `app: show cited articles in expanders` |
| `eval` | الاختبار والتقييم | `eval: add 10 out-of-scope questions` |
| `docs` | التوثيق والتقرير | `docs: explain team workflow` |
| `fix` | إصلاح خطأ | `fix: handle article numbers with bis` |
| `chore` | ترتيب وإعدادات | `chore: update gitignore` |

### قواعد الكتابة

1. **بالإنجليزية البسيطة**، وجملة قصيرة (حتى 60 حرفًا تقريبًا).
2. **ابدؤوا بفعل أمر:** `add` أضفتُ، `fix` أصلحتُ، `remove` حذفتُ، `update` عدّلتُ، `rename` غيّرتُ الاسم.
3. **commit واحد = فكرة واحدة.** لا نجمع عشرة أشياء في commit واحد.
4. **اعملوا commit كلما اشتغل شيء صغير**، لا في نهاية اليوم فقط.
5. لا نقطة في نهاية الرسالة.

### ✅ جيد وليس جيدًا

| ✅ جيد | ❌ سيئ |
|---|---|
| `collect: skip files already downloaded` | `update` |
| `fix: strip page headers before splitting` | `fix bug` |
| `search: filter articles by valid_to date` | `final` |
| `docs: add commit message examples` | `asdf` |
| | `changes + new stuff + other things` |

### إن احتجتم شرحًا أطول

أضيفوا رسالة ثانية بـ`-m` أخرى:

<div dir="ltr">

```bash
git commit -m "versions: close old version on repeal" -m "Set valid_to and status=repealed so repealed articles never appear as current."
```

</div>

### حين تعملون ثنائيًا (pair)

اكتبوا اسم زميلكم ليُنسب له العمل أيضًا:

<div dir="ltr">

```bash
git commit -m "search: add BM25 baseline" -m "Co-authored-by: Name <his-email-on-github@example.com>"
```

</div>

---

## 4. Pull Request (طلب الدمج)

الـPull Request (اختصاره PR) هو **طلب منكم لدمج فرعكم في `main`**، يراجعه زميل قبل الدمج.

### كيف أفتح PR؟

1. **العنوان:** مثل رسالة الـcommit (`collect: add polite PDF downloader`).
2. **الوصف:** اكتبوا ثلاثة أسطر:
   - **ماذا فعلت؟**
   - **كيف أجرّبه؟** (أمر أو خطوات)
   - **المهمة:** `Closes #5` (رقم الـIssue، فيُغلق تلقائيًا عند الدمج)
3. **Reviewers:** اختاروا زميلًا واحدًا على الأقل (**ليس أنتم**).
4. اضغطوا **Create pull request**.

### قواعد الـPR

- **PR صغير:** مهمة واحدة، وتُقرأ في دقائق. PR ضخم لا يقرؤه أحد جيدًا.
- **المراجعة خلال 24 ساعة** (أو قولوا لنا إن كنتم مشغولين).
- **بعد موافقة زميل** يضغط صاحب الـPR زر الدمج، بخيار **Create a merge commit** (وليس Squash). هكذا تبقى كل commits منسوبة لأصحابها.
- بعد الدمج: **Delete branch**.
- لا ندمج PR يخلو من أي مراجعة، حتى لو كان صغيرًا.

### مراجعة PR زميل (للمراجِع)

اسألوا أنفسكم:
- [ ] هل فهمتُ ما فعله؟ (إن لم أفهم فأسأل)
- [ ] هل يعمل؟ (جرّبته أو قرأته بانتباه)
- [ ] هل فيه مفتاح سري (`.env`) أو ملف كبير أو بيانات لا مكان لها في Git؟
- [ ] هل الأسماء متسقة مع الباقي؟

وللتعليق:
- ✅ **كونوا محترمين ومحددين:** «ما رأيك أن نسمّيها `valid_to`؟» أو «لم أفهم هذا السطر، هل تشرحه؟»
- ✅ استعملوا زر **Suggest changes** لاقتراح تعديل صغير.
- ❌ **لا تعيدوا كتابة كود زميلكم بأنفسكم.** اقترحوا وليُعدّل هو.
- ❌ لا تنتقدوا الشخص، انتقدوا الكود.

---

## 5. ملف `.env` والمفاتيح السرية

**ما هو `.env`؟** ملف نصي عندكم في جهازكم فقط، فيه الأسرار (مثل مفتاح Gemini):

<div dir="ltr">

```text
GEMINI_API_KEY=your_key_here
```

</div>

### القواعد

- ✅ **لكل واحد مفتاحه الخاص** من Google AI Studio، ولا نتبادل المفاتيح.
- ✅ ملف `.gitignore` يمنع رفع `.env`، **لكن تأكدوا بأنفسكم:** قبل كل commit شغّلوا `git status`، وإن ظهر `.env` فتوقفوا واسألوا.
- ❌ لا تكتبوا المفتاح داخل الكود، ولا في Issue أو PR أو رسالة commit، ولا في لقطة شاشة.
- في الكود اقرؤوه من البيئة (`os.environ["GEMINI_API_KEY"]`).

### إن رفعتم مفتاحًا بالخطأ

لا تكتفوا بحذف الملف، فـGit **يحفظ التاريخ** ويبقى المفتاح فيه.

1. **اذهبوا فورًا إلى Google AI Studio واحذفوا المفتاح** وأنشئوا مفتاحًا جديدًا.
2. **أخبروا الفريق** (لا عقاب، فهذا يحدث).
3. ضعوا المفتاح الجديد في `.env` عندكم.

---

## 6. الملفات الكبيرة والبيانات

- ❌ **لا نرفع** ملفات PDF للجريدة الرسمية ولا قواعد البيانات ولا ملفات الـcache إلى Git. مجلد `data/` **خارج Git**.
- GitHub **يرفض** أي ملف أكبر من 100 MB.
- ✅ **سكربتات التحميل** تُرفع، فيستطيع كل واحد إعادة إنتاج البيانات عنده.
- ✅ البيانات المشتركة نضعها في المجلد المشترك: **[ضعوا هنا رابط المجلد المشترك]**

---

## 7. دفاتر Jupyter

- الأفضل كتابة الكود في ملفات `.py`.
- إن استعملتم دفترًا (`.ipynb`) فامسحوا المخرجات قبل الـcommit (في VS Code: **Clear All Outputs**).
- لا يعمل شخصان على الدفتر نفسه في الوقت نفسه، فتعارضات الدفاتر مؤلمة.

---

## 8. مشاكل شائعة وحلولها

### «رفض `git push`» (rejected)

سبب ذلك أن أحدًا رفع شيئًا قبلكم. شغّلوا `git pull` ثم `git push` من جديد.

### «تعارض» (merge conflict)

يعني أن شخصين عدّلا السطر نفسه. افتحوا الملف وسترون علامات:

<div dir="ltr">

```text
<<<<<<< HEAD
your version
=======
their version
>>>>>>> main
```

</div>

اختاروا النسخة الصحيحة (أو ادمجوهما)، **واحذفوا العلامات الثلاث** (`<<<<<<<` و`=======` و`>>>>>>>`)، ثم:

<div dir="ltr">

```bash
git add the-file
git commit
```

</div>

وإن لم تكونوا متأكدين مما تختارون، **اسألوا صاحب السطر الآخر**.

### «عملتُ على `main` بالخطأ ولم أرفع بعد»

<div dir="ltr">

```bash
git switch -c my-new-branch        # your work moves to a new branch
git add .
git commit -m "module: what I did" # make sure EVERYTHING is committed on the new branch
git switch main
git reset --hard origin/main       # main goes back to the GitHub version
```

</div>

⚠️ `git reset --hard` **يمحو** كل تغيير لم يُسجَّل بـcommit. لا تشغّلوه قبل الـcommit، وإن ترددتم فاسألوا أولًا.
وإن كنتم **رفعتم** إلى `main` فعلًا فاكتبوا للفريق ولا تحاولوا الإصلاح وحدكم.

### «أريد التراجع عن تعديل في ملف لم أحفظه»

<div dir="ltr">

```bash
git restore the-file
```

</div>

⚠️ هذا يعيد الملف كما كان ويمحو تعديلاتكم عليه.

### «لا أعرف أين أنا!»

<div dir="ltr">

```bash
git status      # which branch? what changed?
git branch      # list of branches (* = current one)
git log --oneline -5   # last 5 commits
```

</div>

---

## 9. قاموس صغير

| الكلمة | معناها |
|---|---|
| **Repository (repo)** | مجلد المشروع مع كل تاريخه |
| **Commit** | لقطة محفوظة من عملكم مع رسالة |
| **Branch** | خط عمل موازٍ لا يمس `main` |
| **Push** | رفع commits من جهازكم إلى GitHub |
| **Pull** | جلب ما رفعه الآخرون |
| **Pull Request (PR)** | طلب دمج فرعكم في `main` |
| **Merge** | دمج فرع في فرع آخر |
| **Conflict** | شخصان عدّلا الموضع نفسه ويجب الاختيار بينهما |
| **Issue** | مهمة أو مشكلة مكتوبة في GitHub |
| **Review** | قراءة زميل لعملكم وتعليقه عليه |

---

## 10. قواعد الاحترام بيننا

- 🤝 **لا أحد يعمل وحده.** إن علقتم فاطلبوا المساعدة.
- 📋 **كل مهمة لها Issue بصاحب وموعد.** نأخذ مهمة بإعلانها لا بالصمت.
- 🚫 لا `git push --force`. ولا نعدّل فرع زميل دون إذنه.
- 💬 إن لم يعجبكم أمر في هذه القواعد فاقترحوا تعديله في اجتماعنا. هذا الملف **يُعدَّل بالاتفاق**.

</div>
