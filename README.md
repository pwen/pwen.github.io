🚀 A blog built with Jekyll and hosted on Github Pages

### Development

```
bundle install
bundle exec jekyll serve
```

Content should be served locally at `http://localhost:4000`

### 📝 Writing a New Post

1. Create a new file in the `_posts` directory
2. Name it with the format: `YYYY-MM-DD-title.md` (for English) or `YYYY-MM-DD-title-zh.md` (for Mandarin)
3. Add the front matter at the top of the file:

**English Post Example:**
```markdown
---
layout: post
title: "Your Post Title"
date: 2026-01-25 10:00:00 -0800
lang: en
tags: [tag1, tag2]
image: /assets/images/your-image.jpg  # Optional
---

Your content here...
```

**Mandarin Post Example:**
```markdown
---
layout: post
title: "你的文章标题"
date: 2026-01-25 10:00:00 -0800
lang: zh
tags: [标签1, 标签2]
image: /assets/images/your-image.jpg  # Optional
---

你的内容在这里...
```

**To add images**:

1. Place your images in the `assets/images/` directory
2. Reference them in your post:
   ```markdown
   ![Image description](/assets/images/your-image.jpg)
   ```
3. Or set as the post's featured image in the front matter:
   ```yaml
   image: /assets/images/your-image.jpg
   ```

#### 🌐 Bilingual Support

This blog supports both English and Mandarin:

- English posts should have `lang: en` in the front matter
- Mandarin posts should have `lang: zh` in the front matter
- The homepage automatically filters posts by language
- The language switcher in the header allows users to toggle between languages

## 📂 Project Structure

```
pwen.github.io/
├── _config.yml           # Site configuration
├── _layouts/             # Page templates
│   ├── default.html      # Base layout
│   ├── home.html         # Homepage layout
│   └── post.html         # Blog post layout
├── _posts/               # Your blog posts
│   ├── 2026-01-25-welcome-to-my-blog.md
│   └── 2026-01-25-welcome-to-my-blog-zh.md
├── assets/
│   ├── css/
│   │   └── style.css     # Main stylesheet
│   └── images/           # Your images
├── index.md              # English homepage
├── zh.md                 # Mandarin homepage
├── about.html            # About page
├── Gemfile               # Ruby dependencies
└── README.md             # This file
```

### 📚 Resources

- [Jekyll Documentation](https://jekyllrb.com/docs/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Markdown Guide](https://www.markdownguide.org/)
- [Liquid Template Language](https://shopify.github.io/liquid/)
