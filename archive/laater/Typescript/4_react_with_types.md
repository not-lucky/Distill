# React with types

## Exercises in this chapter

**React with types**

> Note: You will not receive points for exercises in this chapter until you lock the chapter and a teacher reviews your answers.

| # | Exercise |
|---|----------|
| 1 | 17. Course, step1 |
| 2 | 18. Course, part2 |
| 3 | 19. Flight diaries, step1 |
| 4 | 20. Flight diaries, step2 |
| 5 | 21. Flight diaries, step3 |
| 6 | 22. Flight diaries, step4 |

---

Before we start delving into how you can use TypeScript with React, we should first have a look at what we want to achieve. When everything works as it should, TypeScript will help us catch the following kinds of errors:

- calling a component with wrong kind or amount of props
- forgetting to set a required prop
- using wrong kind of props, e.g. setting a string where a number is expected
- trying to access a property that does not exist on an object

If we make any of these errors, TypeScript can help us catch them in our editor right away. If we do not use TypeScript, we have to catch these errors later during testing. We might be forced to do so in production if the tests are not comprehensive enough.

That's enough reasoning for now. Let's start getting our hands dirty!

## Vite with TypeScript

We can use [Vite](https://vitejs.dev/) to create a TypeScript app specifying a template `react-ts` in the initialization script. So to create a TypeScript app, run the following command:

```bash
npm create vite@latest my-app-name -- --template react-ts
```

After running the command, you should have a complete basic React app that uses TypeScript. You can start the app by running `npm run dev`.

If you take a look at the files and folders, you'll notice that the app is not that different from one using pure JavaScript. The only differences are that the `.jsx` files are now `.tsx` files, they contain TypeScript, and there is a `tsconfig.app.json` file.

Now, let's take a look at the `tsconfig.app.json` file that has been created for us:

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2023",
    "useDefineForClassFields": true,
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "types": ["vite/client"],
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}
```

The *compilerOptions* now include the key *lib* with *DOM*, which adds type definitions for browser environment APIs such as *document*. Most of the other configs are more or less obvious or already familiar to us.

In our previous project, we used ESLint to help us enforce a coding style, and we'll do the same with this app. We do not need to install any dependencies, since Vite has taken care of that already.

When we look at the *main.tsx* file that Vite has generated, it looks familiar, but there is a small but remarkable difference; there is an exclamation mark after the statement `document.getElementById('root')`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

The reason for this is that the statement might return value null but the `ReactDOM.createRoot` does not accept null as parameter. With the [! operator](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#non-null-assertion-operator-postfix-), it is possible to assert to the TypeScript compiler that the value is not null.

Earlier in this part, we [warned](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3) about the dangers of type assertions, but in our case, the assertion is ok since we are sure that the file *index.html* indeed has this particular id and the function is always returning an HTMLElement.

## React components with TypeScript

Let us consider the following JavaScript React example:

```jsx
import ReactDOM from 'react-dom/client'

const Welcome = props => {  
  return <h1>Hello, {props.name}</h1>;
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <Welcome name="Sarah" />
)
```

In this example, we have a component called *Welcome* to which we pass a *name* as a prop. It then renders the name to the screen. We know that the *name* should be a string. In React, there is no way to ensure that the component is used correctly.

> In older React versions, it was possible to define expected types for component props and receive warnings about type mismatches using the [prop-types](https://www.npmjs.com/package/prop-types) feature, but support for this has been removed in React 19.

With TypeScript, we can define the types with the help of TypeScript, just like we define types for a regular function, as React components are nothing but mere functions. We will use an interface for the parameter types (i.e., props) and *JSX.Element* as the return type for any React component:

```tsx
import ReactDOM from 'react-dom/client'

interface WelcomeProps {
  name: string;
}

const Welcome = (props: WelcomeProps): JSX.Element => {
  return <h1>Hello, {props.name}</h1>;
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Welcome name="Sarah" />
)
```

We defined a new type, *WelcomeProps*, and passed it to the function's parameter types.

```tsx
const Welcome = (props: WelcomeProps): JSX.Element => {
```

You could write the same thing using a more verbose syntax:

```tsx
const Welcome = ({ name }: { name: string }): JSX.Element => (
  <h1>Hello, {name}</h1>
);
```

Now our editor knows that the *name* prop is a string.

There is actually no need to define the return type of a React component since the TypeScript compiler infers the type automatically, so we can just write:

```tsx
interface WelcomeProps {
  name: string;
}

const Welcome = (props: WelcomeProps) => {
  return <h1>Hello, {props.name}</h1>;
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <Welcome name="Sarah" />
)
```

---

### Exercise:17. Course, step1

**0/1**

**Instructions**

Create a new Vite app with TypeScript in the directory `course` of your submission repository.

This exercise is similar to the one you have already done in [Part 1](https://fullstackopen.com/en/part1/java_script#exercises-1-3-1-5) of the course, but with TypeScript and some extra tweaks. Start off by modifying the contents of `main.tsx` to match:

```tsx
import ReactDOM from 'react-dom/client'
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <App />
)
```

and *App.tsx*:

```tsx
const App = () => {
  const courseName = "Half Stack application development";
  const courseParts = [
    {
      name: "Fundamentals",
      exerciseCount: 10
    },
    {
      name: "Using props to pass data",
      exerciseCount: 7
    },
    {
      name: "Deeper type usage",
      exerciseCount: 14
    }
  ];

  const totalExercises = courseParts.reduce((sum, part) => sum + part.exerciseCount, 0);

  return (
    <div>
      <h1>{courseName}</h1>
      <p>
        {courseParts[0].name} {courseParts[0].exerciseCount}
      </p>
      <p>
        {courseParts[1].name} {courseParts[1].exerciseCount}
      </p>
      <p>
        {courseParts[2].name} {courseParts[2].exerciseCount}
      </p>
      <p>
        Number of exercises {totalExercises}
      </p>
    </div>
  );
};

export default App;
```

and remove the unnecessary files.

The whole app is now in one component. That is not what we want, so refactor the code so that it consists of three components: *Header*, *Content* and *Total*. All data is still kept in the *App* component, which passes all necessary data to each component as props. *Be sure to add type declarations for each component's props!*

The *Header* component should take care of rendering the name of the course. *Content* should render the names of the different parts and the number of exercises in each part, and *Total* should render the total sum of exercises in all parts.

The *App* component should look somewhat like this:

```tsx
const App = () => {
  // const-declarations

  return (
    <div>
      <Header name={courseName} />
      <Content ... />
      <Total ... />
    </div>
  )
};
```

---

## Deeper type usage

In the previous exercise, we had three parts of a course, and all parts had the same attributes *name* and *exerciseCount*. But what if we need additional attributes for a specific part? How would this look, codewise? Let's consider the following example:

```ts
const courseParts = [
  {
    name: "Fundamentals",
    exerciseCount: 10,
    description: "This is an awesome course part"
  },
  {
    name: "Using props to pass data",
    exerciseCount: 7,
    groupProjectCount: 3
  },
  {
    name: "Basics of type Narrowing",
    exerciseCount: 7,
    description: "How to go from unknown to string"
  },
  {
    name: "Deeper type usage",
    exerciseCount: 14,
    description: "Confusing description",
    backgroundMaterial: "https://type-level-typescript.com/template-literal-types"
  },
];
```

In the above example, we have added some additional attributes to each course part. Each part has the *name* and *exerciseCount* attributes, but the first, third and fourth also have an attribute called *description*. The second and fourth parts also have some distinct additional attributes.

Let's imagine that our application just keeps on growing, and we need to pass the different course parts around in our code. On top of that, there are also additional attributes and course parts added to the mix. How can we know that our code is capable of handling all the different types of data correctly, and we are not for example forgetting to render a new course part on some page? This is where TypeScript comes in handy!

Let's start by defining types for our different course parts. We notice that the first and third have the same set of attributes. The second and fourth are a bit different so we have three different kinds of course part elements.

So let us define a type for each of the different kind of course parts:

```ts
interface CoursePartBasic {
  name: string;
  exerciseCount: number;
  description: string;
  kind: "basic"
}

interface CoursePartGroup {
  name: string;
  exerciseCount: number;
  groupProjectCount: number;
  kind: "group"
}

interface CoursePartBackground {
  name: string;
  exerciseCount: number;
  description: string;
  backgroundMaterial: string;
  kind: "background"
}
```

Besides the attributes that are found in the various course parts, we have now introduced an additional attribute called *kind* that has a [literal](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#literal-types) type, it is a "hard coded" string, distinct for each course part. We shall soon see where the attribute kind is used!

Next, we will create a type [union](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#union-types) of all these types. We can then use it to define a type for our array, which should accept any of these course part types:

```ts
type CoursePart = CoursePartBasic | CoursePartGroup | CoursePartBackground;
```

Now we can set the type for our *courseParts* variable:

```tsx
const App = () => {
  const courseName = "Half Stack application development";
  const courseParts: CoursePart[] = [
    {
      name: "Fundamentals",
      exerciseCount: 10,
      description: "This is an awesome course part",
      kind: "basic"
    },
    {
      name: "Using props to pass data",
      exerciseCount: 7,
      groupProjectCount: 3,
      kind: "group"
    },
    {
      name: "Basics of type Narrowing",
      exerciseCount: 7,
      description: "How to go from unknown to string",
      kind: "basic"
    },
    {
      name: "Deeper type usage",
      exerciseCount: 14,
      description: "Confusing description",
      backgroundMaterial: "https://type-level-typescript.com/template-literal-types",
      kind: "background"
    },
  ];
  // ...
};
```

Our editor will automatically warn us if we use the wrong type for an attribute, use an extra attribute, or forget to set an expected attribute. If we e.g. try to add the following to the array

```ts
{
  name: "TypeScript in frontend",
  exerciseCount: 10,
  kind: "basic",
},
```

We will immediately see an error in the editor:

![VS Code editor showing a type error warning that the property 'description' is missing in type '{ name: string; exerciseCount: number; kind: "basic"; }' but required in type 'CoursePartBasic'. The error is highlighted on the object literal with kind "basic" that is missing the required description field.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/Zsx8ev650g06RBzYvLDSYQ1gVilFzJ.png)

Since our new entry has the attribute *kind* with value *"basic"*, TypeScript knows that the entry does not only have the type *CoursePart* but it is actually meant to be a *CoursePartBasic*. So here the attribute *kind* "narrows" the type of the entry from a more general to a more specific type that has a certain set of attributes. We shall soon see this structure in action!

But we're not satisfied yet! There is still a lot of duplication in our types, and we want to avoid that. We start by identifying the attributes all course parts have in common, and defining a base type for them. We can then [extend](https://www.typescriptlang.org/docs/handbook/2/objects.html#extending-types) the base type to create the specific types:

```ts
interface CoursePartBase {
  name: string;
  exerciseCount: number;
}

interface CoursePartBasic extends CoursePartBase {
  description: string;
  kind: "basic"
}

interface CoursePartGroup extends CoursePartBase {
  groupProjectCount: number;
  kind: "group"
}

interface CoursePartBackground extends CoursePartBase {
  description: string;
  backgroundMaterial: string;
  kind: "background"
}

type CoursePart = CoursePartBasic | CoursePartGroup | CoursePartBackground;
```

## More type narrowing

How should we now use these types in our components?

If we try to access the objects in the array `courseParts: CoursePart[],` we notice that it is possible to only access the attributes that are common to all the types in the union:

![VS Code editor showing autocomplete suggestions for a course part object. Only the common attributes 'name' and 'exerciseCount' are available in the dropdown, demonstrating that TypeScript only allows accessing attributes shared by all union members.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/VIMPFw84f68vNgwCXw0Qxcd6lfTLGR.png)

And indeed, the TypeScript [documentation](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#working-with-union-types) says this:

> TypeScript will only allow an operation (or attribute access) if it is valid for every member of the union.

The documentation also mentions the following:

> The solution is to narrow the union with code... Narrowing occurs when TypeScript can deduce a more specific type for a value based on the structure of the code.

So once again the [type narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) is the rescue!

One handy way to narrow these kinds of types in TypeScript is to use switch case expressions. Once TypeScript has inferred that a variable is of union type and that each type in the union contains a common attribute with a literal type, it can narrow the type based on the value of that attribute:

![VS Code editor showing a switch statement narrowing the type of a course part. In each case block ("basic", "group", "background"), the autocomplete shows additional type-specific attributes: 'description' for basic, 'groupProjectCount' for group, and 'description' and 'backgroundMaterial' for background.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/LID27xwoPigfMh4bL1OTwe5YVOtxaQ.png)

In the above example, TypeScript knows that a *part* has the type *CoursePart* and it can then infer that *part* is of either type *CoursePartBasic*, *CoursePartGroup* or *CoursePartBackground* based on the value of the attribute *kind*.

The specific technique of type narrowing where a union type is narrowed based on literal attribute value is called [discriminated union](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#discriminated-unions).

Note that the narrowing can naturally be also done with *if* clause. We could eg. do the following:

```ts
courseParts.forEach(part => {
  if (part.kind === 'background') {
    console.log('see the following:', part.backgroundMaterial)
  }

  // can not refer to part.backgroundMaterial here!
});
```

What about adding new types? If we were to add a new course part, wouldn't it be nice to know if we had already implemented handling that type in our code? In the example above, a new type would go to the *default* block and nothing would get printed for a new type. Sometimes this is wholly acceptable. For instance, if you wanted to handle only specific (but not all) cases of a type union, having a default is fine. Nonetheless, it is recommended to handle all variations separately in most cases.

With TypeScript, we can use a method called [exhaustive type checking](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#exhaustiveness-checking). Its basic principle is that if we encounter an unexpected value, we call a function that accepts a value with the type [never](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#the-never-type).

A straightforward version of the function could look like this:

```ts
/**
 * Helper function for exhaustive type checking
 */
const assertNever = (value: never): never => {
  throw new Error(
    `Unhandled discriminated union member: ${JSON.stringify(value)}`
  );
};
```

If we now were to replace the contents of our *default* block to:

```ts
default:
  return assertNever(part);
```

and remove the case that handles the type *CoursePartBackground*, we would see the following error:

![VS Code editor showing a TypeScript error: "Argument of type 'CoursePartBackground' is not assignable to parameter of type 'never'." The error is highlighted on the 'part' variable in the assertNever() call within the default case of a switch statement, indicating that not all union types are handled.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/V82LSprzcJWg7CwrYO6LqzVymz3WSv.png)

The error message says that

```
'CoursePartBackground' is not assignable to parameter of type 'never'.
```

which tells us that we are using a variable somewhere where it should never be used. This tells us that something is wrong — we have not handled all the possible cases.

---

### Exercise:18. Course, part2

**0/1**

**Instructions**

Let us now continue extending the app created in the previous exercise. First, add the type information and replace the variable courseParts with the one from the example below.

```ts
interface CoursePartBase {
  name: string;
  exerciseCount: number;
}

interface CoursePartBasic extends CoursePartBase {
  description: string;
  kind: "basic"
}

interface CoursePartGroup extends CoursePartBase {
  groupProjectCount: number;
  kind: "group"
}

interface CoursePartBackground extends CoursePartBase {
  description: string;
  backgroundMaterial: string;
  kind: "background"
}

type CoursePart = CoursePartBasic | CoursePartGroup | CoursePartBackground;

const courseParts: CoursePart[] = [
  {
    name: "Fundamentals",
    exerciseCount: 10,
    description: "This is an awesome course part",
    kind: "basic"
  },
  {
    name: "Using props to pass data",
    exerciseCount: 7,
    groupProjectCount: 3,
    kind: "group"
  },
  {
    name: "Basics of type Narrowing",
    exerciseCount: 7,
    description: "How to go from unknown to string",
    kind: "basic"
  },
  {
    name: "Deeper type usage",
    exerciseCount: 14,
    description: "Confusing description",
    backgroundMaterial: "https://type-level-typescript.com/template-literal-types",
    kind: "background"
  },
  {
    name: "TypeScript in frontend",
    exerciseCount: 10,
    description: "a hard part",
    kind: "basic",
  },
];
```

Now we know that both interfaces *CoursePartBasic* and *CoursePartBackground* share not only the base attributes but also an attribute called *description*, which is a string in both interfaces.

Your **first task** is to declare a new interface that includes the *description* attribute and extends the *CoursePartBase* interface. Then modify the code so that you can remove the *description* attribute from both *CoursePartBasic* and *CoursePartBackground* without getting any errors.

**Then** create a component *Part* that renders all attributes of each type of course part. Use a switch case-based exhaustive type checking! Use the new component in the component *Content*.

**Now**, add another course part interface with the following attributes: *name*, *exerciseCount*, *description,* and *requirements*, the latter being a string array. The objects of this type look like the following:

```ts
{
  name: "Backend development",
  exerciseCount: 21,
  description: "Typing the backend",
  requirements: ["nodejs", "jest"],
  kind: "special"
}
```

**Then** add that interface to the type union *CoursePart* and add the corresponding data to the *courseParts* variable. Now, if you have not modified your *Content* component correctly, you should get an error, because you have not yet added support for the fourth course part type.

And **lastly**, do the necessary changes to Content so that all attributes for the new course part also get rendered, and that the compiler doesn't produce any errors.

The result might look like the following:

![A web application UI displaying a course titled "Half Stack application development" with a list of course parts. Each part shows its name, exercise count, and type-specific details: descriptions for basic parts, group project count for group parts, background material links for background parts, and requirements list for special parts. A total count of 59 exercises is shown at the bottom.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/o7UGkttEVjgjVuXid4vuY4VhHrNj9W.png)

---

## React app with state

We start with the following code:

```tsx
import { useState } from 'react';

const App = () => {
  const [newNote, setNewNote] = useState('');
  const [notes, setNotes] = useState([]);

  return null
}
```

When we hover over the *useState* calls in the editor, we notice a couple of interesting things.

The type of the first call `useState('')` looks like the following:

```ts
useState<string>(initialState: string | (() => string)):
  [string, React.Dispatch<React.SetStateAction<string>>]
```

The type is somewhat challenging to decipher. It has the following "form":

```ts
functionName(parameters): return_value
```

So we notice that TypeScript compiler has inferred that the initial state is either a string or a function that returns a string:

```ts
initialState: string | (() => string))
```

The type of the returned array is the following:

```ts
[string, React.Dispatch<React.SetStateAction<string>>]
```

So the first element, assigned to *newNote* is a string and the second element that we assigned *setNewNote* is a function used to set the state.

From all this we see that TypeScript has indeed [inferred](https://www.typescriptlang.org/docs/handbook/type-inference.html#handbook-content) the type of the first useState correctly, a state with type string is created.

When we look at the second useState that has the initial value `[]`, the type looks quite different

```ts
useState<never[]>(initialState: never[] | (() => never[])): 
  [never[], React.Dispatch<React.SetStateAction<never[]>>] 
```

TypeScript can just infer that the state has type *never[]*, it is an array but it has no clue what the elements stored to the array are, so we clearly need to help the compiler and provide the type explicitly.

One of the best sources for information about typing React is the [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/). The Cheatsheet chapter about [useState](https://react-typescript-cheatsheet.netlify.app/docs/basic/getting-started/hooks#usestate) hook instructs us to use a *type parameter* in situations where the compiler can not infer the type.

Let us now define a type for notes:

```ts
interface Note {
  id: string,
  content: string
}
```

The solution is now simple:

```ts
const [notes, setNotes] = useState<Note[]>([]);
```

And indeed, the type is set correctly:

```ts
useState<Note[]>(initialState: Note[] | (() => Note[])):
  [Note[], React.Dispatch<React.SetStateAction<Note[]>>]
```

So in technical terms useState is [a generic function](https://www.typescriptlang.org/docs/handbook/2/generics.html#working-with-generic-type-variables), where the type has to be specified as a *type parameter* in those cases when the compiler can not infer the type.

Rendering the notes is now easy. Let us just add some data to the state so that we can see that the code works:

```tsx
interface Note {
  id: string,
  content: string
}

import { useState } from "react";

const App = () => {
  const [notes, setNotes] = useState<Note[]>([
    { id: '1', content: 'testing' }
  ]);
  const [newNote, setNewNote] = useState('');

  return (
    <div>
      <ul>
        {notes.map(note =>
          <li key={note.id}>{note.content}</li>
        )}
      </ul>
    </div>
  )
}
```

![VS Code editor showing that event.target.value is correctly typed as string. The hover tooltip displays "(parameter) event: React.ChangeEvent<HTMLInputElement>" with the target property expanded to show value is a string.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/vVomlFS4AhyHb52qbvmFzp1Pf1Vu5a.png)

So we still need the event handler for adding the new note. Let us try the following:

```tsx
const App = () => {
  // ...
  const noteCreation = (event) => {
    event.preventDefault()
    // ...
  };
  return (
    <div>
      <form onSubmit={noteCreation}>
        <input
          value={newNote}
          onChange={(event) => setNewNote(event.target.value)}
        />
        <button type='submit'>add</button>
      </form>
      // ...
    </div>
  )
}
```

TypeScript compiler now has no clue what the type of the parameter is, this is why the type is the infamous implicit any that we want to [avoid](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3) at all costs. The React TypeScript cheatsheet has a chapter about [forms and events](https://react-typescript-cheatsheet.netlify.app/docs/basic/getting-started/forms_and_events) that gives us the right type.

![VS Code editor showing a TypeScript error highlighting the 'event' parameter in a function. The error message states "Parameter 'event' implicitly has an 'any' type" with a red squiggly underline beneath the event parameter.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/vBI9RtyFa0EiyvwH08jJd2zsYd79D1.png)

The code becomes

```tsx
interface Note {
  id: string,
  content: string
}

const App = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState('');

  const noteCreation = (event: React.SyntheticEvent) => {
    event.preventDefault()
    const noteToAdd = {
      content: newNote,
      id: String(notes.length + 1)
    }
    setNotes(notes.concat(noteToAdd));
    setNewNote('')
  };

  return (
    <div>
      <form onSubmit={noteCreation}>
        <input value={newNote} onChange={(event: React.SyntheticEvent) => setNewNote(event.target.value)} />
        <button type='submit'>add</button>
      </form>
      <ul>
        {notes.map(note =>
          <li key={note.id}>{note.content}</li>
        )}
      </ul>
    </div>
  )
}
```

## Communicating with the server

Let us modify the app so that the notes are saved in a JSON server backend in url [http://localhost:3001/notes](http://localhost:3001/notes)

As usual, we shall use Axios and the useEffect hook to fetch the initial state from the server.

Let us try the following:

```tsx
import axios from 'axios';

// ...

const App = () => {
  // ...
  useEffect(() => {
    axios.get('http://localhost:3001/notes').then(response => {
      console.log(response.data);
    })
  }, [])
  // ...
}
```

When we hover over the `response.data` we see that it has the type *any*

![VS Code editor showing a hover tooltip over response.data with the type displayed as "any", indicating that TypeScript cannot infer the response data type from the untyped axios.get call.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/CoBLSdcrPuic5CbFQArRJH4QOnszu5.png)

To set the data to the state with function *setNotes* we must type it properly.

With a little [help from the internet](https://upmostly.com/typescript/how-to-use-axios-in-your-typescript-apps), we find a clever trick:

```tsx
useEffect(() => {
  axios.get<Note[]>('http://localhost:3001/notes').then(response => {
    console.log(response.data);
  })
}, [])
```

When we hover over the response.data we see that it has the correct type:

![VS Code editor showing a hover tooltip over response.data displaying the type "Note[]" — an array of Note objects with id (string) and content (string) properties — after adding a generic type parameter to axios.get.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/HNDPCggmln9hXO9NxmW15ReRD290HL.png)

We can now set the data in the state *notes* to get the code working:

```tsx
useEffect(() => {
  axios.get<Note[]>('http://localhost:3001/notes').then(response => {
    setNotes(response.data)
  })
}, [])
```

So just like with *useState*, we gave a type parameter to *axios.get* to instruct it on how the typing should be done. Just like *useState*, *axios.get* is also a [generic function](https://www.typescriptlang.org/docs/handbook/2/generics.html#working-with-generic-type-variables). Unlike some generic functions, the type parameter of *axios.get* has a default value of *any* so, if the function is used without defining the type parameter, the type of the response data will be any.

The code works, the compiler and ESLint are happy and remain quiet. However, giving a type parameter to `axios.get` is a potentially dangerous thing to do. The *response body could contain data in an arbitrary form*, and when giving a type parameter, we are essentially just telling the TypeScript compiler to trust us that the data has type *Note[]*.

So our code is essentially as safe as it would be if a [type assertion](https://fullstackopen.com/en/part9/first_steps_with_type_script#type-assertion) would be used (not good):

```tsx
useEffect(() => {
  axios.get('http://localhost:3001/notes').then(response => {
    // response.body is of type any
    setNotes(response.data as Note[])
  })
}, [])
```

Since the TypeScript types do not even exist in runtime, our code does not give us any safety against situations where the request body contains data in the wrong form.

Giving a type parameter to *axios.get* might be ok if we are *absolutely sure* that the backend behaves correctly and always returns the data in the correct form. If we want to build a robust system we should prepare for surprises and parse the response data (similar to what we did [in the previous section](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-4) for the requests to the backend).

Let us now wrap up our app by implementing the new note addition:

```tsx
const noteCreation = (event: React.SyntheticEvent) => {
  event.preventDefault()
  axios.post<Note>('http://localhost:3001/notes', { content: newNote })
    .then(response => {
      setNotes(notes.concat(response.data))
    })
  setNewNote('')
};
```

Let us clean up the code a bit. For the type definitions, we create a file *types.ts* with the following content:

```ts
export interface Note {
  id: string,
  content: string
}

export type NewNote = Omit<Note, 'id'>
```

We have added a new type for a *new note*, one that does not yet have the *id* field assigned.

The code that communicates with the backend is also extracted to a module in the file *noteService.ts*

```ts
import axios from 'axios'
import type { Note, NewNote } from './types'

const baseUrl = 'http://localhost:3001/notes'

const getAll = () => {
  return axios
    .get<Note[]>(baseUrl)
    .then(response => response.data)
}

const create = (object: NewNote) => {
  return axios
    .post<Note>(baseUrl, object)
    .then(response => response.data)
}

export default { getAll, create }
```

The component *App* is now much cleaner:

```tsx
import { useState, useEffect } from 'react'
import type { Note } from './types'
import noteService from './noteService'

const App = () => {
  const [notes, setNotes] = useState<Note[]>([]);
  const [newNote, setNewNote] = useState('');

  useEffect(() => {
    noteService.getAll().then(initialNotes => {
      setNotes(initialNotes)
    })
  }, [])

  const noteCreation = (event: React.SyntheticEvent) => {    
    event.preventDefault()
    noteService.create({ content: newNote })
      .then(returnedNote => {
        setNotes(notes.concat(returnedNote))
      })
    setNewNote('')
  };

  return (
    // ...
  )
}

export default App
```

The app is now nicely typed and ready for further development!

The code of the typed notes can be found [here](https://github.com/fullstack-hy2020/typed-notes).

## A note about defining object types

We have used [interfaces](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#interfaces) to define object types, e.g. diary entries, in the previous section

```ts
interface DiaryEntry {
  id: number;
  date: string;
  weather: Weather;
  visibility: Visibility;
  comment?: string;
} 
```

and in the course part of this section

```ts
interface CoursePartBase {
  name: string;
  exerciseCount: number;
}
```

We actually could have achieved the same effect by using a [type alias](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#type-aliases)

```ts
type DiaryEntry = {
  id: number;
  date: string;
  weather: Weather;
  visibility: Visibility;
  comment?: string;
} 
```

In most cases, you can use either *type* or *interface*, whichever syntax you prefer. However, there are a few things to keep in mind. For example, if you define multiple interfaces with the same name, they will result in a merged interface, whereas if you try to define multiple types with the same name, it will result in an error stating that a type with the same name is already declared.

TypeScript documentation [recommends using interfaces](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#differences-between-type-aliases-and-interfaces) in most cases.

---

### Exercise:19. Flight diaries, step1

**0/1**

**Instructions**

Let us now build a frontend for Ilari's flight diaries that was developed in [the previous chapter](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-4). The application goes to the directory `flightdiaries` in your submission repository and the frontend you are about to create goes to the subdirectory `frontend`.

Create a TypeScript React app with similar configurations to the apps of this chapter. The code should be in the directory `flightdiaries/frontend`.

Fetch the diaries from the backend and render those to the screen. Do all the required typing and ensure that there are no ESLint errors.

Remember to keep the network tab open. It might give you a valuable hint...

You can decide how the diary entries are rendered. Note that the backend API does not return the diary comments. You may modify it to return also those on a GET request if you wish.

The result might look like the following:

![A simple web UI showing flight diary entries displayed as a list. Each entry shows a date, weather condition, and visibility level. Below the list is a form for adding new diary entries with fields for date, weather, visibility, and a comment textarea, along with a submit button.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/EhjGLciBINfx0oPEAQTTC93MWVsJ52.png)

---

### Exercise:20. Flight diaries, step2

**0/1**

**Instructions**

Add a form for creating new diary entries to the frontend. The form should contain fields for date, weather, visibility, and comment. The form should be well-typed, and there should be no ESLint errors.

---

### Exercise:21. Flight diaries, step3

**0/1**

**Instructions**

Notify the user if the the creation of a diary entry fails in the backend, show also the reason for the failure.

See eg. [this](https://dev.to/mdmostafizurrahaman/handle-axios-error-in-typescript-4mf9) to see how you can narrow the Axios error so that you can get hold of the error message.

Your solution may look like this:

![A form with a date picker (DayPicker calendar component), and radio buttons for selecting weather and visibility. The weather options include sunny, rainy, cloudy, stormy, and windy. The visibility options include great, good, ok, and poor. There is also a comment textarea and an Add button.](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/TPE0XS0eN4uP0JcbXUOvTNlEzax30a.png)

---

### Exercise:22. Flight diaries, step4

**0/1**

**Instructions**

Modify the input form so that the date is set with a HTML [date](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/date) input element, and the weather and visibility are set with HTML [radio buttons](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/radio). We already did something similar in [part 6](https://fullstackopen.com/en/part6/many_reducers#store-with-complex-state) of the Full Stack Open course.

Your app should always stay well-typed, with no ESLint errors and no ESLint rules ignored.

Your solution could look like this:

---

## Mark Chapter as Complete
