// The rules in plain English, in the order the engine names them (src/sentinel/rules.py, docs/THREAT_MODEL.md).
// `outcome` is the decision word the rule produces. Limits are stated here too: the page must not oversell.
export const RULES = [
  { id: 'R1', title: 'Stay inside the slip', outcome: 'DENIED',
    text: 'The tool and the destination must be on the permission slip, and the tool must be one Sentinel knows. Anything else is refused, including a tool nobody has classified.' },
  { id: 'R2', title: 'Restricted data stays in', outcome: 'DENIED',
    text: 'A value the agent read from a restricted source (quantities, codes, dates, addresses, identifiers, copied passages) may not appear in anything leaving the building. A paraphrase of confidential prose can still slip through; we list that as a declared gap.' },
  { id: 'R3', title: 'No addresses from documents', outcome: 'DENIED',
    text: 'An address that appears only in an untrusted document is not used as a destination.' },
  { id: 'R4', title: 'The officer confirms sensitive changes', outcome: 'NEEDS APPROVAL',
    text: 'Some actions, such as changing a vendor’s bank account, run only if the officer approves that exact request.' },
  { id: 'R5', title: 'A message limit', outcome: 'DENIED',
    text: 'The slip says how many messages may go out. After that, none.' },
  { id: 'R6', title: 'Three strikes', outcome: 'QUARANTINED',
    text: 'The third denied action freezes that session and revokes its token. Other sessions are not affected.' },
  { id: 'R7', title: 'After untrusted reading, ask first', outcome: 'NEEDS APPROVAL',
    text: 'Once the agent has read an untrusted document, page or message, a consequential action goes only to a place the slip names as internal, or waits for the officer. It can hold some valid actions too.' },
]

export const PRECEDENCE = 'When more than one rule applies, the strictest wins: freeze, then deny, then ask, then allow.'
