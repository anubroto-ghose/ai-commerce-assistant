import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { API_BASE } from './config'

const LANG_STORAGE_KEY = 'walmart_genai_lang'
const newSessionId = () => (window.crypto?.randomUUID ? window.crypto.randomUUID() : `${Date.now()}-${Math.random()}`)

function F({ k, r }) {
  return (
    <ruby>
      {k}
      <rt>{r}</rt>
    </ruby>
  )
}

const I18N = {
  en: {
    brand: 'Walmart GenAI Product Assistant',
    title: 'Natural-Language Product Discovery',
    subtitle: 'Search products semantically, inspect reviews, and get smarter alternatives.',
    search: 'Search',
    queryPlaceholder: 'Show me highly rated shampoos with natural ingredients',
    maxResults: 'Max results',
    searching: 'Searching...',
    searchButton: 'Search',
    filters: 'Detected filters:',
    suggestion: 'Suggested search:',
    useSuggestion: 'Use suggestion',
    detectedLanguage: 'Detected language',
    any: 'any',
    results: 'Results',
    emptyResults: 'Run a query to view products.',
    productId: 'Product ID',
    rating: 'Rating',
    brandLabel: 'Brand',
    delivery: 'Delivery',
    pickup: 'Pickup',
    yes: 'Yes',
    no: 'No',
    moreDetails: 'More details',
    colors: 'Colors',
    ingredients: 'Ingredients',
    na: 'N/A',
    chatbot: 'Product Chatbot',
    chatLauncher: 'Chat Assistant',
    you: 'You',
    ai: 'AI',
    newChat: 'New Chat',
    session: 'Session',
    openChat: 'Open chat',
    closeChat: 'Close',
    chatAboutProduct: 'Ask about this product',
    workflow: 'Workflow: ask a question, provide Product ID, receive review summary and alternatives for low-rated products.',
    chatPlaceholder: 'What do people say about this product?',
    ask: 'Ask',
    analyzing: 'Analyzing...',
    provideId: 'Please provide Product ID.',
    alternatives: 'Better-rated alternatives',
    language: 'Language'
  },

  jp: {
    brand: (
      <>
        ウォルマート GenAI <F k="商品" r="しょうひん" />アシスタント
      </>
    ),

    title: (
      <>
        <F k="自然言語" r="しぜんげんご" />
        <F k="商品" r="しょうひん" />
        <F k="検索" r="けんさく" />
      </>
    ),

    subtitle: (
      <>
        セマンティック<F k="検索" r="けんさく" />、
        レビュー<F k="解析" r="かいせき" />、
        より<F k="良" r="よ" />い<F k="代替案" r="だいたいあん" />を<F k="提案" r="ていあん" />。
      </>
    ),

    search: <F k="検索" r="けんさく" />,

    queryPlaceholder: '自然成分の高評価シャンプーを見せて',

    maxResults: <><F k="表示件数" r="ひょうじけんすう" /></>,

    searching: <><F k="検索中" r="けんさくちゅう" />...</>,

    searchButton: <F k="検索" r="けんさく" />,

    filters: (
      <>
        <F k="検出" r="けんしゅつ" />された<F k="条件" r="じょうけん" />:
      </>
    ),
    suggestion: (
      <>
        <F k="提案検索" r="ていあんけんさく" />:
      </>
    ),
    useSuggestion: (
      <>
        <F k="提案" r="ていあん" />を<F k="使" r="つか" />う
      </>
    ),
    detectedLanguage: (
      <>
        <F k="検出言語" r="けんしゅつげんご" />
      </>
    ),

    any: <><F k="指定" r="してい" />なし</>,

    results: <F k="結果" r="けっか" />,

    emptyResults: (
      <>
        クエリを<F k="実行" r="じっこう" />すると
        <F k="商品" r="しょうひん" />が<F k="表示" r="ひょうじ" />されます。
      </>
    ),

    productId: <><F k="商品" r="しょうひん" />ID</>,

    rating: <F k="評価" r="ひょうか" />,

    brandLabel: "ブランド",

    delivery: <F k="配送" r="はいそう" />,

    pickup: <><F k="店舗" r="てんぽ" /><F k="受取" r="うけとり" /></>,

    yes: "はい",

    no: "いいえ",

    moreDetails: <F k="詳細" r="しょうさい" />,

    colors: "カラー",

    ingredients: <F k="成分" r="せいぶん" />,

    na: "なし",

    chatbot: <><F k="商品" r="しょうひん" />チャットボット</>,
    chatLauncher: <><F k="チャット" r="ちゃっと" />アシスタント</>,
    you: 'あなた',
    ai: 'AI',
    newChat: <><F k="新規" r="しんき" />チャット</>,
    session: <><F k="セッション" r="せっしょん" /></>,
    openChat: <><F k="開" r="ひら" />く</>,
    closeChat: <><F k="閉" r="と" />じる</>,
    chatAboutProduct: (
      <>
        この<F k="商品" r="しょうひん" />について<F k="質問" r="しつもん" />
      </>
    ),

    workflow: (
      <>
        <F k="質問" r="しつもん" />を<F k="入力" r="にゅうりょく" />し、
        <F k="商品" r="しょうひん" />IDを<F k="入力" r="にゅうりょく" />すると
        レビュー<F k="要約" r="ようやく" />と
        <F k="代替商品" r="だいたいしょうひん" />を<F k="表示" r="ひょうじ" />します。
      </>
    ),

    chatPlaceholder: 'この商品の評判はどう？',

    ask: <F k="質問" r="しつもん" />,

    analyzing: <><F k="解析中" r="かいせきちゅう" />...</>,

    provideId: (
      <>
        <F k="商品" r="しょうひん" />IDを<F k="入力" r="にゅうりょく" />してください。
      </>
    ),

    alternatives: (
      <>
        より<F k="評価" r="ひょうか" />の<F k="高" r="たか" />い
        <F k="代替商品" r="だいたいしょうひん" />
      </>
    ),

    language: <F k="言語" r="げんご" />
  }
}

function App() {
  const [lang, setLang] = useState(() => {
    const saved = typeof window !== 'undefined' ? window.localStorage.getItem(LANG_STORAGE_KEY) : null
    return saved === 'jp' || saved === 'en' ? saved : 'en'
  })
  const t = I18N[lang]

  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(5)
  const [results, setResults] = useState([])
  const [filters, setFilters] = useState({})
  const [suggestedSearch, setSuggestedSearch] = useState('')
  const [detectedLanguage, setDetectedLanguage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [chatMessage, setChatMessage] = useState('')
  const [chatProductId, setChatProductId] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatResponse, setChatResponse] = useState(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatLog, setChatLog] = useState([])
  const [chatSessionId, setChatSessionId] = useState(() => newSessionId())

  const hasResults = useMemo(() => results.length > 0, [results])

  useEffect(() => {
    window.localStorage.setItem(LANG_STORAGE_KEY, lang)
  }, [lang])

  const runSearch = async (overrideQuery = null) => {
    const effectiveQuery = typeof overrideQuery === 'string' ? overrideQuery : query
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: effectiveQuery, limit: Number(limit) })
      })
      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Search failed')
      }
      const payload = await response.json()
      setResults(payload.products || [])
      setFilters(payload.interpreted_filters || {})
      setSuggestedSearch(payload.suggested_search || '')
      setDetectedLanguage(payload.detected_language || '')
    } catch (err) {
      setError(err.message)
      setResults([])
      setSuggestedSearch('')
      setDetectedLanguage('')
    } finally {
      setLoading(false)
    }
  }

  const askChatbot = async () => {
    if (!chatMessage.trim()) return
    setChatLoading(true)
    setError('')
    const userText = chatMessage
    setChatLog((prev) => [...prev, { role: 'user', text: userText }])
    setChatMessage('')
    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, product_id: chatProductId || null, session_id: chatSessionId })
      })
      if (!response.ok) {
        const payload = await response.json()
        throw new Error(payload.detail || 'Chat request failed')
      }
      const payload = await response.json()
      setChatResponse(payload)
      setChatSessionId(payload.session_id || chatSessionId)
      setChatLog((prev) => [...prev, { role: 'assistant', text: payload.response }])
    } catch (err) {
      setError(err.message)
      setChatResponse(null)
      setChatLog((prev) => [...prev, { role: 'assistant', text: err.message }])
    } finally {
      setChatLoading(false)
    }
  }

  const openChatForProduct = (productId) => {
    setChatOpen(true)
    setChatProductId(productId)
  }

  const startNewChat = () => {
    setChatSessionId(newSessionId())
    setChatLog([])
    setChatResponse(null)
    setChatMessage('')
    setChatProductId('')
  }

  const onSearchKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      runSearch()
    }
  }

  const onChatKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      askChatbot()
    }
  }

  const yesNo = (value) => (value ? t.yes : t.no)

  return (
    <div className="page-shell">
      <header className="hero">
        <div className="hero-topbar">
          <p className="eyebrow">{t.brand}</p>
          <div className="language-switch" role="group" aria-label={t.language}>
            <button
              className={lang === 'en' ? 'active' : ''}
              onClick={() => setLang('en')}
            >
              English
            </button>

            <button
              className={lang === 'jp' ? 'active' : ''}
              onClick={() => setLang('jp')}
            >
              日本語
            </button>
          </div>
        </div>
        <h1>{t.title}</h1>
        <p className="subtitle">{t.subtitle}</p>
      </header>

      <section className="panel">
        <h2>{t.search}</h2>
        <div className="search-row">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onSearchKeyDown}
            placeholder={t.queryPlaceholder}
            rows={2}
          />
          <label>
            {t.maxResults}
            <input
              type="number"
              min="1"
              max="15"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
            />
          </label>
          <button onClick={() => runSearch()} disabled={loading}>{loading ? t.searching : t.searchButton}</button>
        </div>

        <div className="filters">
          <span>{t.filters}</span>
          <code>price ≤ {filters.max_price ?? t.any}</code>
          <code>rating ≥ {filters.min_rating ?? t.any}</code>
          <code>category: {filters.category ?? t.any}</code>
          {detectedLanguage && <code>{t.detectedLanguage}: {detectedLanguage}</code>}
        </div>
        {suggestedSearch && (
          <div className="suggestion-row">
            <span>{t.suggestion} <strong>{suggestedSearch}</strong></span>
            <button
              type="button"
              onClick={() => {
                setQuery(suggestedSearch)
                runSearch(suggestedSearch)
              }}
            >
              {t.useSuggestion}
            </button>
          </div>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel">
        <h2>{t.results}</h2>
        {!hasResults && <p className="empty">{t.emptyResults}</p>}
        <div className="results-grid">
          {results.map((product) => (
            <article key={product.product_id} className="card">
              <img src={product.main_image} alt={product.product_name} loading="lazy" />
              <p className="breadcrumb">{product.breadcrumb}</p>
              <h3>{product.product_name}</h3>
              <p>{product.description}</p>
              <div className="meta-row">
                <span>{t.productId}: {product.product_id}</span>
                <span>{product.currency} {product.price?.toFixed(2)}</span>
              </div>
              <div className="meta-row">
                <span>{t.rating}: {product.rating} ({product.review_count})</span>
                <span>{t.brandLabel}: {product.brand || t.na}</span>
              </div>
              <div className="meta-row">
                <span>{t.delivery}: {yesNo(product.available_for_delivery)}</span>
                <span>{t.pickup}: {yesNo(product.available_for_pickup)}</span>
              </div>
              <details>
                <summary>{t.moreDetails}</summary>
                <p><strong>{t.colors}:</strong> {(product.colors || []).join(', ') || t.na}</p>
                <p><strong>{t.ingredients}:</strong> {product.ingredients || t.na}</p>
                <ul>
                  {(product.specifications || []).slice(0, 6).map((spec, index) => (
                    <li key={`${product.product_id}-${index}`}>{spec.name}: {spec.value}</li>
                  ))}
                </ul>
              </details>
              <button className="ghost-btn" onClick={() => openChatForProduct(product.product_id)}>
                {t.chatAboutProduct}
              </button>
            </article>
          ))}
        </div>
      </section>

      <button className="chat-fab" onClick={() => setChatOpen((v) => !v)} aria-label={t.openChat}>
        🤖
      </button>
      {chatOpen && (
        <section className="floating-chat">
          <div className="floating-chat-header">
            <h3>{t.chatLauncher}</h3>
            <div className="chat-header-actions">
              <button className="ghost-btn" onClick={startNewChat}>{t.newChat}</button>
              <button className="ghost-btn" onClick={() => setChatOpen(false)}>{t.closeChat}</button>
            </div>
          </div>
          <p className="session-id">{t.session}: {chatSessionId.slice(0, 8)}</p>
          <p className="hint">{t.workflow}</p>
          <div className="chat-history">
            {chatLog.map((entry, idx) => (
              <div key={`${entry.role}-${idx}`} className={`chat-row ${entry.role}`}>
                <div className={`chat-bubble ${entry.role}`}>
                  <p className="chat-role">{entry.role === 'user' ? t.you : t.ai}</p>
                  <span>{entry.text}</span>
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="chat-row assistant">
                <div className="chat-bubble assistant typing">
                  <p className="chat-role">{t.ai}</p>
                  <span>{t.analyzing}</span>
                </div>
              </div>
            )}
          </div>
          <div className="floating-chat-inputs">
            <input value={chatProductId} onChange={(e) => setChatProductId(e.target.value)} placeholder={t.productId} />
            <textarea
              value={chatMessage}
              onChange={(e) => setChatMessage(e.target.value)}
              onKeyDown={onChatKeyDown}
              placeholder={t.chatPlaceholder}
              rows={2}
            />
            <button onClick={askChatbot} disabled={chatLoading}>{chatLoading ? t.analyzing : t.ask}</button>
          </div>
          {chatResponse?.needs_product_id && <p className="hint">{t.provideId}</p>}
          {chatResponse?.alternatives?.length > 0 && (
            <div className="chat-panel">
              <h3>{t.alternatives}</h3>
              <ul>
                {chatResponse.alternatives.map((item) => (
                  <li key={`alt-${item.product_id}`}>
                    {item.product_name} ({item.rating}) - {item.currency} {item.price?.toFixed(2)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}
    </div>
  )
}

export default App
