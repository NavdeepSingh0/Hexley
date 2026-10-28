import { Shot } from './Ui.jsx'

// A numbered list of steps, each a few words beside a real screenshot; alternate rows are flipped.
// steps: [{ n, title, text, shot, alt, caption, id? }]
export default function Story({ steps }) {
  return (
    <ol className="story">
      {steps.map((s, i) => (
        <li key={s.n} id={s.id} className={`story-step${i % 2 ? ' is-flipped' : ''}`}>
          <div className="story-copy">
            <span className="story-n" aria-hidden="true">{s.n}</span>
            <h3 className="story-title">{s.title}</h3>
            <p className="story-text">{s.text}</p>
          </div>
          <figure className="story-fig">
            <Shot name={s.shot} alt={s.alt} />
            <figcaption>{s.caption}</figcaption>
          </figure>
        </li>
      ))}
    </ol>
  )
}
