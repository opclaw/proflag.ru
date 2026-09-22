# ТЗ разработчику proflag.ru — технические исправления

Порядок исполнения = порядок разделов. Каждый пункт самодостаточен для постановки в задачу.

## 1. Хостинг и поддомены (P0)

1.1. **print.proflag.ru** отдаёт заглушку reg.ru «Сайт размещен некорректно» (server14.hosting.reg.ru).
- Вариант A (быстро): настроить 301 со всех URL print.proflag.ru/* → https://www.proflag.ru/katalog/pechat-na-tkani/
- Вариант B (правильно): развернуть на поддомене лендинг услуги «Печать на ткани».
- Пункт меню «Печать на ткани» в шаблоне перевести с `https://print.proflag.ru/` на `https://www.proflag.ru/katalog/pechat-na-tkani`.

1.2. Проверить и настроить 301-редиректы: `http://proflag.ru` → `https://www.proflag.ru`, `https://proflag.ru` → `https://www.proflag.ru` (единый канонический хост, HSTS опционально).

## 2. robots.txt (P0)

Текущие проблемные правила:
```
Disallow: /images/          ← закрыты ВСЕ картинки сайта
Disallow: /privacy-policy   ← закрыта страница ПД
Disallow: *?*               ← запрещены все GET-параметры (в т.ч. пагинация статей ?start=)
Allow: /?option=com_ajax&plugin=flyandexturbo
```

Требуемые правки:
1. Удалить `Disallow: /images/` (индексация изображений). Служебную графику (`/templates/`, `/images/system/`) можно оставить закрытой.
2. Удалить `Disallow: /privacy-policy`.
3. Заменить `Disallow: *?*` на точечные:
```
Disallow: /*?etext=
Disallow: /*?cm_id=
Disallow: /*?source_type=
Disallow: /*?utm_
Disallow: /*?start=   ← если решено не индексировать пагинацию; иначе Clean-param
```
4. Для Яндекса добавить `Clean-param: start /articles` (или разрешить пагинацию с canonical).
5. Сверить, что в robots и sitemap нет противоречий (`/vsja-produkcija` vs `/katalog/vsja-produkcija`).

## 3. Мета и разметка (P0)

3.1. **Open Graph** на всех страницах:
```html
<meta property="og:type" content="website">
<meta property="og:site_name" content="Профлаг">
<meta property="og:title" content="…">
<meta property="og:description" content="…">
<meta property="og:image" content="https://www.proflag.ru/images/og/proflag-cover.jpg"> (1200×630)
<meta property="og:url" content="…">
```
В Joomla — шаблон + плагин (например, ReReplacer/шаблонные переопределения), og:image по умолчанию = обложка категории.

3.2. **JSON-LD Organization + LocalBusiness** на главной и /kontakty:
```json
{
  "@context":"https://schema.org",
  "@type":"LocalBusiness",
  "name":"Профлаг",
  "telephone":["+7 (495) 128-10-18","8 (800) 100-10-18"],
  "email":"info@proflag.ru",
  "address":{"@type":"PostalAddress","addressLocality":"Москва","streetAddress":"ул. Уткина, д. 48, стр. 4","postalCode":"105275"},
  "geo":{"@type":"GeoCoordinates","latitude":55.772074,"longitude":37.690023},
  "openingHours":"Mo-Fr 09:30-18:00",
  "url":"https://www.proflag.ru/",
  "logo":"https://www.proflag.ru/…/logo.svg",
  "sameAs":["https://t.me/ProflagMoscow","https://vk.com/…","https://youtube.com/…"]
}
```

3.3. **BreadcrumbList** на всех вложенных страницах.

3.4. На карточках товаров (после появления): `Product` + `Offer` (price, priceCurrency RUB, availability) + `AggregateRating` (синхронизировать с Яндекс.Картами) + `FAQPage` на категориях с FAQ-блоком.

## 4. Контент и шаблон (P0–P1)

4.1. **Битые лайтбоксы портфолио**: ссылки вида `https://www.proflag.ru/raboty/images/portfolio/…` → заменить на `/images/portfolio/…` (проверить все ~130 страниц /raboty/*, массовая замена в БД Joomla).

4.2. **Текст в картинках**: блоки преимуществ главной (`preim-ser1.png…`) заменить на HTML-текст с иконками — сейчас контент невидим роботу.

4.3. H1 главной: сейчас `# Профлаг` → «Производство флагов, флагштоков и текстиля с логотипом в Москве». Подзаголовок — оффер «Образец за 1 час, тираж от 5 часов, доставка по РФ».

4.4. Заголовки-картинки («Рассчитаем стоимость заказа за 15 минут» как H2-ссылки) → обычный HTML.

4.5. Шаблонные блоки («Преимущества заказа в Профлаг», «Видео с производства») убрать со всех категорий, оставить на главной/о компании. Для категорий — уникальные тексты (см. action-plan п.13).

4.6. Соцкнопки: удалить Skype, «Мой Мир» (закрыт), Instagram, Facebook; VK/Telegram/YouTube — нативные виджеты без внешних тяжёлых скриптов.

4.7. CTA в категориях: `tel:+7(965)2823618` → единый номер 8-800/495; рядом кнопки WhatsApp/Telegram (глубокие ссылки wa.me/t.me) с UTM-метками.

## 5. Скорость (P1)

5.1. Включить кэширование страниц Joomla (System Cache, консервативно), Gzip/Brotli на сервере, заголовки Cache-Control для статики.
5.2. Изображения: конвертация в WebP (кроме логотипов-масок PNG → SVG), `loading="lazy"` для всего ниже первого экрана, явные width/height (сейчас CLS от каруселей).
5.3. Объединить/минифицировать CSS/JS (JCH Optimize или аналог), отложить сторонние скрипты (виджеты, share-кнопки).
5.4. Карусель брендов: убрать тройное дублирование `<img>` (сейчас логотипы выводятся 3 раза подряд для «бесконечности» — делать через CSS-анимацию дубликата DOM, а не тройной HTML).
5.5. Целевые метрики: HTML ≤ 150 КБ; TTFB ≤ 0,5 с; LCP ≤ 2,5 с (мобайл); CLS ≤ 0,1.
5.6. Рассмотреть переезд с shared-хостинга reg.ru на VPS (nginx + PHP-FPM + FastCGI cache) — текущая генерация ~3 с.

## 6. Sitemap (P1)

6.1. Генерировать sitemap с `<lastmod>` (дата последнего изменения контента).
6.2. Убрать из sitemap служебные/сезонные неактуальные URL либо поддерживать их актуальность (даты, акции).
6.3. После добавления карточек товаров — включить их в sitemap автоматически.

## 7. Каталог и e-commerce (P1–P2)

7.1. Карточки готовых позиций (флаг РФ, Победы, флажки настольные): URL вида `/katalog/flag/flagi-rossii/flag-rossii-90x135/`, цена, наличие, кнопка «Быстрый заказ» (имя+тел) и «В корзину» (если строим корзину).
7.2. Калькулятор: тип изделия → размер → тираж → ткань → срочность; выдаёт диапазон цены и форму с прикреплением файла макета (до 20 МБ, ai/pdf/png/psd). Результат отправляется в CRM/на почту с UTM.
7.3. Формы: добавить поле загрузки макета во все основные формы; событие Метрики на успешную отправку (`form_send`), цели в Яндекс.Метрике; антиспам (honeypot).

## 8. Контроль качества (после работ)

- Яндекс.Вебмастер: переобход sitemap, «Проверка ответа сервера», региональность = Москва.
- GSC: отправка sitemap, запрос индексации топ-20 страниц.
- Screaming Frog / SEOmator (github.com/seo-skills/seo-audit-skill, 332 правила): прогнать сайт после правок, обнулить 4xx/5xx, битые внутренние ссылки, дублей title/h1.
- PSI: замерить до/после (квота API в день аудита была исчерпана).
