# SNePSpaCy Guide 🧭

You talk to SNePS in English. Statements become facts in the knowledge base, and questions are answered from those facts and from everything SNePS can infer from them. Every example below is a real session.

## Starting ⌨️

```bash
python main.py
```

Set it up first as described in the [README](README.md#installation-%EF%B8%8F). With `python main.py --api-mode off` you only see how sentences are translated, without SNePS.

## Telling and asking 💬

* A sentence ending in `.` is **told**: `<T>` shows its SNePSLOG, and it becomes a fact.
* A sentence ending in `?` is **asked**: `<A>` shows each answer.

```
//: John ate an apple.
<T> eat(eac0c) and agent(eac0c, John) and object(eac0c, a57fc) and apple(a57fc) and culminate(eac0c, PAST)
//: Who ate the apple?
<A> culminate(eac0c,PAST) and apple(a57fc) and object(eac0c,a57fc) and agent(eac0c,John) and eat(eac0c)
```

An answer is the question with its unknowns filled in: "who" became `agent(eac0c, John)`, so the answer is John. Things without names get references like `a57fc`, the apple (`apple(a57fc)`), and `eac0c`, the eating.

`No answer found.` means SNePS neither knows it nor can infer it:

```
//: Did Mary eat the apple?
<A> No answer found.
```

## What it understands 📚

One example of each kind of sentence and question.

### Who did what

```
//: John ate an apple.
//: What did John eat?
<A> culminate(eac0c,PAST) and object(eac0c,a57fc) and agent(eac0c,John) and eat(eac0c)
//: Did John eat the apple?
<A> culminate(eac0c,PAST) and apple(a57fc) and object(eac0c,a57fc) and agent(eac0c,John) and eat(eac0c)
```

Verbs are stored by their base form with the tense apart (`eat` and `culminate(…, PAST)`), so "ate", "has eaten" and "did eat" all match.

### Passive

```
//: The cake was eaten by Bob.
//: Who ate the cake?
<A> culminate(e093b,PAST) and agent(e093b,Bob) and cake(c3c4f) and object(e093b,c3c4f) and eat(e093b)
```

Active and passive sentences give the same facts.

### Where, when, why, how, how many, whose

```
//: John lives in Paris.
//: Where does John live?
<A> location(e89e6,Paris) and agent(e89e6,John) and live(e89e6)

//: Mary left yesterday.
//: When did Mary leave?
<A> culminate(eb41f,PAST) and time(eb41f,y94e7) and agent(eb41f,Mary) and leave(eb41f)

//: Sue left because she was tired.
//: Why did Sue leave?
<A> culminate(eb41f,PAST) and cause(eb41f,s720e) and agent(eb41f,Sue) and leave(eb41f)

//: Tom ran quickly.
//: How did Tom run?
<A> culminate(ec964,PAST) and manner(ec964,quickly) and agent(ec964,Tom) and run(ec964)

//: Three dogs barked.
//: How many dogs barked?
<A> culminate(e231c,PAST) and quantity(three,dfb46) and dog(dfb46) and agent(e231c,dfb46) and bark(e231c)

//: Ann's cat slept.
//: Whose cat slept?
<A> culminate(ef225,PAST) and possessor(c4c48,Ann) and cat(c4c48) and agent(ef225,c4c48) and sleep(ef225)
```

The answers are `location(…, Paris)`, `time(…, y94e7)` (yesterday), `cause(…, s720e)` (her being tired), `manner(…, quickly)`, `quantity(three, …)` and `possessor(…, Ann)`.

### States

```
//: Alice is happy.
//: Is Alice happy?
<A> happy(Alice) and happy(m009f) and content(se285,m009f) and reference(se285,Alice) and state(se285)

//: Alice is taller than Bob.
//: Is Alice taller than Bob?
<A> taller_than(m5e88,Bob) and content(s129e,m5e88) and reference(s129e,Alice) and state(s129e)
```

### Referring back

"the", "he", "she" and "it" refer to what was mentioned before, and several sentences can be typed at once:

```
//: John left. He ran.
<T> (leave(e7b33) and agent(e7b33, John) and …) and (run(ec964) and agent(ec964, John) and …)
```

"He" became John. In the examples above, "she" in "Sue left because she was tired" became Sue, and "the apple" in "Who ate the apple?" became `a57fc`, the apple John ate.

### Reasoning 🧠

These answers were never told; SNePS infers them.

```
//: Socrates is a man.
//: Every man is mortal.
//: Is Socrates mortal?
<A> state(s129e(Socrates)) and reference(s129e(Socrates),Socrates) and content(s129e(Socrates),m9c5a(Socrates)) and mortal(m9c5a(Socrates)) and mortal(Socrates)
```

Plurals said in general are rules too:

```
//: Dogs bark.
//: Rex is a dog.
//: Does Rex bark?
<A> bark(ea07d(Rex)) and agent(ea07d(Rex),Rex)
```

With "every … a …", each one gets their own:

```
//: Every boy loves a dog.
//: Tom is a boy.
//: Does Tom love a dog?
<A> love(e3a38(Tom)) and agent(e3a38(Tom),Tom) and object(e3a38(Tom),d3dec(Tom)) and dog(d3dec(Tom))
```

`d3dec(Tom)` is Tom's own dog.

"If" makes a rule that SNePS uses as soon as the condition is told:

```
//: If it rains, Bob stays.
//: It rains.
//: Does Bob stay?
<A> stay(e8916(e83a7)) and agent(e8916(e83a7),Bob)
```

### Not and or

These are stored, and SNePS reasons with them:

```
//: John did not eat the apple.
<T> all(e31a4)(~eat(e31a4) or ~agent(e31a4, John) or ~object(e31a4, a57fc) or ~apple(a57fc) or ~culminate(e31a4, PAST))
//: John or Mary left.
<T> leave(eb41f) and (agent(eb41f, John) or agent(eb41f, Mary)) and culminate(eb41f, PAST)
```

Questions only look for what is true, so "Did John eat the apple?" and "Did John leave?" find no answer here.

## Console commands 🛠️

* `list-wffs`: everything SNePS believes now, told or inferred.
* `ask <SNePSLOG>`: ask SNePS directly, for example `ask mortal(Socrates)` gives `mortal(Socrates)`.
* `clearkb`: start over, forgetting all facts and what was mentioned.
* `exit`: leave. Up/Down recall earlier input and Ctrl+L clears the screen.

## Limits ⚠️

* "he", "she" and "it" refer to the most recently mentioned name or thing.
* Relative clauses describe a thing but are not facts of their own: after "The house where Ann lives is big", SNePS does not know where Ann lives.
* Not handled yet: "can", "must", "want to", "think that", "everyone", "nobody", and "before", "after" or "although" clauses. These are being worked on in the `attempt-general` branch.
