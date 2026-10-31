# Publicador automático · Hábitos Fix Hoy

Tu propio "Metricool", gratis y sin límite de plan. Cada 30 minutos revisa `calendario.csv` y publica solo en **Instagram, Facebook y YouTube** todo lo que ya tenga la hora cumplida. Después anota en el mismo calendario si salió bien o qué error hubo.

Lo configurás **una sola vez** (más o menos 1 hora). Después no tenés que autorizar nada más: lo que esté en el calendario, sale.

---

## Paso 1 · Crear el repositorio en GitHub (5 min)

1. Entrá a GitHub con tu cuenta **bienestarpleno11-dev**.
2. Arriba a la derecha: **+** → **New repository**.
3. Nombre: `publicador`. Marcá **Public** (así GitHub te lo corre gratis sin límite de minutos). Tocá **Create repository**.
4. Tocá **uploading an existing file** y arrastrá **todo el contenido** de esta carpeta (incluida la carpeta `.github`). Abajo, **Commit changes**.

> Si la carpeta `.github` no se ve en Windows: en el Explorador, pestaña **Vista** → tildá **Elementos ocultos**.

---

## Paso 2 · Conectar Instagram y Facebook (20 min)

**Antes:** tu Instagram @habitosfixhoy tiene que ser cuenta **profesional** y estar vinculada a la página de Facebook de Hábitos Fix Hoy (si ya andaba con Metricool, ya lo está).

1. Entrá a **developers.facebook.com** con la cuenta de Facebook que administra la página → **Mis apps** → **Crear app**.
2. Elegí el caso de uso para **administrar una página / contenido** (tipo **Empresa**). Ponele de nombre `Publicador HFH`.
3. Dentro de la app, agregá los productos **Inicio de sesión con Facebook para empresas** e **Instagram** (API con inicio de sesión de Facebook).
4. En **Configuración → Básica** copiá el **Identificador de la app** y la **Clave secreta**.
5. Abrí el **Explorador de la API Graph** (developers.facebook.com/tools/explorer):
   - Arriba a la derecha elegí tu app `Publicador HFH`.
   - En **Permisos** agregá: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `business_management`.
   - Tocá **Generate Access Token**, aceptá todo y **marcá tu página y tu Instagram**.
   - Copiá el token que aparece (empieza con `EAA`).
6. Abrí el archivo **`conectar-meta.html`** (doble clic, se abre en tu navegador). Pegá los 3 datos y tocá el botón.
7. Te da 3 claves permanentes. Cargalas en GitHub: tu repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**, una por una, con estos nombres exactos:
   - `META_PAGE_ID`
   - `META_PAGE_TOKEN`
   - `META_IG_USER_ID`

> La app queda en "modo desarrollo" y está bien así: como vos sos el dueño, puede publicar en tus propias cuentas sin pasar revisión.

---

## Paso 3 · Conectar YouTube (20 min)

Usá la cuenta **bienestarpleno11@gmail.com** (la del canal habitosfixhoy).

1. Entrá a **console.cloud.google.com** → arriba, **Seleccionar proyecto** → **Proyecto nuevo** → nombre `publicador-hfh` → Crear.
2. Menú → **APIs y servicios** → **Biblioteca** → buscá **YouTube Data API v3** → **Habilitar**.
3. **APIs y servicios** → **Pantalla de consentimiento de OAuth** (o "Google Auth Platform"): tipo **Externo**, nombre `Publicador HFH`, tu email en soporte y contacto. Guardá.
4. **Muy importante:** en **Público / Audiencia**, tocá **Publicar app** (pasar a "En producción"). Si la dejás "En prueba", el permiso de YouTube vence cada 7 días.
5. **Credenciales** → **Crear credenciales** → **ID de cliente de OAuth** → tipo **Aplicación web**. En **URI de redireccionamiento autorizados** agregá:
   `https://developers.google.com/oauthplayground`
   Crear. Copiá el **ID de cliente** y el **Secreto del cliente**.
6. Entrá a **developers.google.com/oauthplayground**:
   - Tocá el engranaje ⚙ (arriba a la derecha) → tildá **Use your own OAuth credentials** → pegá ID y secreto.
   - A la izquierda, en el cuadro de abajo, escribí: `https://www.googleapis.com/auth/youtube.upload` → **Authorize APIs**.
   - Elegí tu cuenta y **el canal habitosfixhoy** (no "Pablo"). Si aparece "Google no verificó esta app": **Configuración avanzada** → **Ir a Publicador HFH** (es tu propia app).
   - Tocá **Exchange authorization code for tokens** y copiá el **Refresh token**.
7. Cargá en GitHub (igual que en el paso 2):
   - `YT_CLIENT_ID`
   - `YT_CLIENT_SECRET`
   - `YT_REFRESH_TOKEN`

---

## Paso 4 · Probar (5 min)

1. En tu repo: pestaña **Actions** → si pregunta, tocá **I understand… enable them**.
2. A la izquierda **Publicar contenido** → **Run workflow** → tildá **Modo prueba** → **Run workflow**.
3. Entrá a la ejecución: vas a ver qué publicaría sin publicar nada.
4. Para la prueba real, poné en el calendario una fila con la hora de ahora y corré **Run workflow** sin tildar prueba. Revisá tus redes.

---

## Cómo cargar contenido

Todo está en **`calendario.csv`** (se puede editar desde GitHub tocando el lápiz ✏, o pedímelo a mí y te lo armo).

| Columna | Qué poner |
|---|---|
| `fecha_hora` | `2026-11-05 19:00` (hora de Argentina) |
| `redes` | `instagram+facebook+youtube`, o solo las que quieras |
| `tipo` | `reel` (video), `imagen`, `carrusel` o `texto` (solo Facebook) |
| `archivo` | Ruta dentro del repo, por ejemplo `contenido/reel-503020.mp4`. Para carrusel, separá con `\|`: `contenido/c1.jpg\|contenido/c2.jpg` |
| `texto` | El copy de la publicación |
| `primer_comentario` | Opcional: el link, que se pone como primer comentario |
| `titulo_youtube` | Opcional: título del Short (se le agrega #Shorts solo) |
| `instagram`, `facebook`, `youtube`, `detalle` | **No los toques**: ahí el publicador anota "publicado" o el error |

Los videos e imágenes van en la carpeta **`contenido/`** (Add file → Upload files).

---

## Límites reales (los pone cada red, no este sistema)

- **Instagram:** hasta 100 publicaciones por día por API (algunas partes de la documentación de Meta dicen 50). Videos verticales 9:16, en MP4.
- **YouTube:** alrededor de 100 subidas por día. Si un Short queda "privado", aparece en `detalle`: en ese caso hay que pedir la verificación del proyecto a Google (te ayudo).
- **Facebook:** sin un límite bajo para tu volumen.
- **GitHub:** cada archivo hasta 100 MB. A veces GitHub demora la corrida programada unos minutos.
- Si falla una publicación, reintenta sola en las siguientes corridas (hasta 3 veces) y deja el motivo en `detalle`.

Contenido educativo, no es asesoramiento financiero.
