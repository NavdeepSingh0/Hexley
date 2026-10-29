import { Link } from 'react-router-dom'

// Short answers a judge asks, each backed by a file in the repository (the docs page names them). Used on the home page.
export const FAQ = [
  {
    q: 'Does an AI model decide what is allowed?',
    a: <>No. The rules are ordinary code that runs outside the model. A document the model reads can talk it into anything; the checks do not read the document for instructions. <Link to="/docs#limits">What is and is not covered</Link>.</>,
  },
  {
    q: 'Why not just tell the model not to leak?',
    a: <>An instruction in the prompt is advice the model can be persuaded to drop. In our recorded runs of one real model, the unprotected setup delivered the restricted data in every usable run on the poisoned quotation. The counts and their limits are in <Link to="/#evidence">the evidence</Link>.</>,
  },
  {
    q: 'Is it a guarantee?',
    a: <>No. It is a measurement on a set of cases we wrote, plus a stated list of routes it does not cover. Nobody who has not read the rules has attacked it yet; that result will be reported on its own line. <Link to="/docs#limits">Limits and honest scope</Link>.</>,
  },
  {
    q: 'What if the attacker rewords the secret?',
    a: <>A reworded paraphrase of confidential prose can get through value matching. It is listed as a declared gap and counted apart. The other defences still apply: the destination must be on the slip, an address that appears only in a document is not used, and after untrusted reading a consequential send waits for the officer.</>,
  },
  {
    q: 'Which AI apps have you actually tested?',
    a: <>Two, each once: Claude.ai (sign-in, 27 Oct 2026) and Claude Code (access token, 29 Oct 2026), with the evidence kept. Others that speak MCP should work and are labelled that way. <Link to="/integrations">Integrations</Link>.</>,
  },
  {
    q: 'Is any of the data real?',
    a: <>No. Every record, mailbox, document and bank detail is synthetic; domains end in <code>.example</code>, and the tools are mocks.</>,
  },
]
