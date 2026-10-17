# WhatsApp scale-up checklist

Zeya runs on the Meta Cloud API number +254 183 325153 (WhatsApp Business account
1139959938382277, Evarest Technologies Ltd), connected to Open Chat Studio as the
"Zeya WhatsApp" messaging provider. Mothers who message Zeya get replies without being
added anywhere. The items below are for scale and for messages that Zeya sends first.

## Limits today

| What | Limit before business verification | After |
|---|---|---|
| Replies to mothers who message Zeya (within 24 h) | no limit on mothers, free | same |
| Messages Zeya starts (reminders, weekly tips) | 250 mothers a day | 1,000 a day, then 10,000, 100,000 and unlimited as quality allows |
| Phone numbers on the account | 2 | 20 |

## 1. Publish the Meta app

1. Put `docs/privacy-policy.md` online with the placeholders filled in. The GitHub
   page of the file works as a public URL.
2. developers.facebook.com → ZEYA → **App settings → Basic**: add the privacy policy
   URL, an app icon (1024×1024), the category (Health) and the contact email.
3. Publish the app. If Meta asks for App Review for `whatsapp_business_messaging`, stop
   and check first: an app that only serves your own business usually does not need it.

## 2. Business verification

business.facebook.com → **Security centre** (or Settings → Business info) → **Start
verification**. Have ready:

- Evarest Technologies Ltd's certificate of incorporation (Business Registration Service)
- the KRA PIN certificate
- the legal name, address and phone exactly as they appear on those documents
- a website or page that shows the same name

Meta reviews it in a few days. Use the same name everywhere, or it is rejected.

## 3. Display name

WhatsApp Manager → **Phone numbers** → +254 183 325153 → **Display name**: `Zeya`.
Meta checks that the name relates to the business. Mention Zeya on the website you used
for verification. If Meta rejects it, try "Zeya by Evarest".

## 4. Payment method

WhatsApp Manager → **Payment settings**: add a card. Replies within 24 h stay free;
Meta charges per message that Zeya starts.

## 5. The template OCS uses

When the 24-hour window has closed, OCS sends Zeya's message inside one template. OCS
looks for exactly this:

- **Name:** `new_bot_message`
- **Category:** Utility
- **Language:** English (`en`), which matches the provider's Template Language Code
- **Body:** a named parameter `{{bot_message}}`, for example:

  > Zeya: {{bot_message}}

- **Sample value:** `Your next ANC visit is coming up. Remember to attend.`

WhatsApp Manager → **Message templates → Create**. After Meta approves it, press
**Refresh** on the provider page in OCS (Team settings → Zeya WhatsApp). The warning
"No template named 'new_bot_message'" should go away.

Notes:

- OCS uses one template language per provider. Swahili-speaking mothers get the English
  wrapper around a Swahili message unless a second provider is set up with `sw`.
- OCS removes newlines from the message inside the template. Meta rejects them in a
  parameter.
- Template messages count against the daily limit above.

## 6. Keep quality high

Meta lowers the limit, or blocks the number, if many people block or report it. Send
only messages mothers agreed to, and keep reminders infrequent.
