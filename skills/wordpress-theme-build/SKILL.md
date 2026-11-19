---
name: wordpress-theme-build
description: Turn a static HTML/CSS/JS design into a custom WordPress theme that the client can edit, covering theme structure, theme.json, enqueueing scripts, block patterns, custom post types and editable content. Use this whenever someone wants to convert a design or static site to WordPress, build a custom or block theme, make sections editable in Gutenberg, add GSAP or other scripts to a theme properly, or asks why their theme edits are lost or their content is hard-coded.
---

# WordPress theme build

The goal is a theme where the design is locked in code and the content is editable in the editor. Hard-coded text in templates is the most common reason clients come back for trivial edits.

## Choose the approach

| Approach | Choose when |
|---|---|
| **Block theme** (`theme.json`, HTML templates) | New build, client edits in the Site Editor, content is mostly standard blocks |
| **Hybrid classic theme** (PHP templates plus `theme.json` and block patterns) | Complex custom markup or heavy animation that needs exact HTML control |
| **Child theme** | Modifying an existing theme; never edit a parent theme directly, since updates overwrite it |

For animated, design-led marketing sites the hybrid approach is usually the pragmatic one: precise markup in PHP, editable content through patterns, fields and the block editor.

## Minimum structure

```
my-theme/
├── style.css            # theme header comment (required)
├── functions.php        # setup, enqueues, registrations
├── theme.json           # palette, type scale, spacing, layout widths
├── index.php            # fallback template (classic/hybrid)
├── front-page.php       # homepage
├── header.php  footer.php
├── template-parts/      # one file per section
├── patterns/            # block patterns (auto-registered)
├── assets/css  assets/js  assets/media
└── screenshot.png       # 1200x900
```

`style.css` header:

```css
/*
Theme Name: My Theme
Author: Your Name
Version: 1.0.0
Requires at least: 6.4
Requires PHP: 8.0
Text Domain: my-theme
*/
```

## Conversion workflow

1. **Freeze the static build.** Finish HTML, CSS and JS first and validate it. Converting a moving target doubles the work.
2. **Split into parts.** Header and footer go to `header.php` and `footer.php` with `wp_head()` and `wp_footer()`. Each homepage section becomes a file in `template-parts/`, loaded with `get_template_part()`.
3. **Move tokens into `theme.json`** (palette, font sizes, spacing, content width) so the editor shows the same choices as the front end. Keep the same values as CSS custom properties; WordPress generates `--wp--preset--*` variables you can alias. If the `webcraft` CLI is available, `webcraft tokens "#brand" --format theme-json -o theme.json` writes a version 3 file from the same values as `tokens.css`.
4. **Enqueue, never hard-code, assets:**

```php
add_action('wp_enqueue_scripts', function () {
    $v = wp_get_theme()->get('Version');
    $uri = get_theme_file_uri('assets');
    wp_enqueue_style('my-theme', "$uri/css/main.css", [], $v);
    wp_enqueue_script('gsap', "$uri/js/vendor/gsap.min.js", [], '3', ['strategy' => 'defer', 'in_footer' => true]);
    wp_enqueue_script('my-theme', "$uri/js/main.js", ['gsap'], $v, ['strategy' => 'defer', 'in_footer' => true]);
});
```

   Bundle libraries locally rather than from a CDN where possible; it avoids a third-party request and a consent question.
5. **Make content editable.** Pick per section:
   - Repeating items with their own pages (services, portfolio, testimonials): a custom post type queried with `WP_Query`.
   - One-off section text and images: block patterns the client inserts and edits, or custom fields.
   - Global items (phone, social links, footer text): the Customizer or a small options page.
   - Navigation: `register_nav_menus()` and `wp_nav_menu()`.
6. **Escape everything on output:** `esc_html()`, `esc_attr()`, `esc_url()`, `wp_kses_post()` for rich text. Wrap strings in `__()` or `esc_html__()` with the text domain.
7. **Images:** use `wp_get_attachment_image()` so `srcset`, `sizes`, dimensions and lazy loading are generated. Register needed sizes with `add_image_size()`.
8. **Theme supports:** `title-tag`, `post-thumbnails`, `editor-styles`, `responsive-embeds`, `html5`, `wp-block-styles`.

## Animation inside WordPress

- Scripts that hide content must not run in the block editor. Enqueue them only on the front end (`wp_enqueue_scripts`, not `enqueue_block_assets`).
- The admin bar shifts sticky headers by 32px (46px on mobile); offset with `body.admin-bar .header { top: var(--wp-admin--admin-bar--height, 32px); }`.
- Caching and optimization plugins that defer or combine JS can break load order. Declare dependencies properly so they are respected, and test with the plugin enabled.
- Content added in the editor will not have your animation attributes. Either apply animations by block class in JS, or provide patterns that include the attributes.

## Do not

- Edit WordPress core or a parent theme.
- Put functionality that should survive a theme switch (custom post types, shortcodes) in the theme when the client may change themes; a small plugin is the right place.
- Query inside loops without resetting (`wp_reset_postdata()`).
- Ship with `WP_DEBUG` notices. Develop with `WP_DEBUG` on.
- Bundle paid plugins or assets whose licence does not allow redistribution.

## Handover checklist

- Client can change every visible text, image, menu item and contact detail without touching code.
- Homepage set under Settings, Reading; permalinks set to post name.
- Favicon (site icon), 404 template, search template, privacy page present.
- A one-page editing guide with screenshots.
- Then run the `launch-qa` skill.
