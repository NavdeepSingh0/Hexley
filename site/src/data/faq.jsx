import { Link } from 'react-router-dom'

// Short answers a judge asks, each backed by a file in the repository (the docs page names them). Used on the home page.
export const FAQ = [
  {
    q: 'Does an AI model decide what is allowed?',
    a: <>No. The rules are ordinary code that runs outside the model. A document the model reads can talk it into anything; the checks do not read the document for instructions. <Link to="/docs/limits">What is and is not covered</Link>.</>,
  },
  {
    q: 'Why not just tell the model not to leak?',
    a: <>An instruction in the prompt is advice the model can be persuaded to drop. In our recorded runs of one real model, the unprotected setup delivered the restricted data in every usable run on the poisoned quotation. The counts and their limits are in <Link to="/#evidence">the evidence</Link>.</>,
  },
  {
    q: 'How is this different from AWS Cedar policies and Microsoft FIDES?',
    a: <>They are good, and we use their ideas. AWS's AgentCore Policy (generally available since March 2026) evaluates Cedar policies in AWS's gateway on the caller, the tool and the tool's parameters; most policies are stateless, and it now has opt-in session-aware ones. Microsoft's FIDES (experimental in Agent Framework since May 2026, Python) labels data inside an agent built with that framework and hides untrusted results from the model. Hexley sits outside the agent, so it can work with an agent nobody can modify, and its policy input is the task a person approved plus what the session has read. We have no formal guarantee, we do not hide data from the model yet, and our evidence is a small set of cases we wrote ourselves. Facts about their products are from their own pages, read on 30 October 2026.</>,
  },
  {
    q: 'Is it a guarantee?',
    a: <>No. It is a measurement on a set of cases we wrote, plus a stated list of routes it does not cover. Nobody who has not read the rules has attacked it yet; that result will be reported on its own line. <Link to="/docs/limits">Limits and honest scope</Link>.</>,
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
  {
    q: 'What does the officer see when asked?',
    a: <>What the action is, where it goes, which data, and the rule's own words, built by the gateway from the exact arguments. The agent cannot edit that text. Approvals are one-time, bound to that exact call, and expire. <Link to="/docs/concepts">Concepts</Link>.</>,
  },
  {
    q: 'Can I check that the log was not edited?',
    a: <>Yes. In the console, finish the guided run and use Verify, then Tamper (change one record), then Verify again, and Restore to put the record back and carry on; in the chat, open Details and use Verify the log.</>,
  },
]
