*chapter 3*
# First steps with TypeScript

<details>
<summary>Exercises in this chapter</summary>

**First steps with TypeScript**

> Note: You will not receive points for exercises in this chapter until you lock the chapter and a teacher reviews your answers.

1. [1. Body mass index](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#e0b05f8b-081b-41de-a7de-e8ed8d0e1811)
2. [2. Exercise calculator](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#203d6d40-9ca2-4a5c-a2af-d6738b03033e)
3. [3. Command line](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#33ce9d86-c188-4175-a197-b4f4455f671a)
4. [4. Express](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#791a03d9-c877-4efb-b26a-fcced2b0d8fd)
5. [5. WebBmi](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#d4b74996-61d0-4c50-b803-8c26abc5f8c1)
6. [6. Eslint](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#4d1c005a-9a09-4395-a322-f9bd469a6652)
7. [7. WebExercises](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#4fe8fe3e-b3e0-48cd-a7e0-b8b5b1ed65e6)
8. [8. Checkup](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#7d395c4f-af73-40ae-a915-01b600ff8f93)

</details>

After the brief introduction to the main principles of TypeScript, we are now ready to start our journey toward becoming FullStack TypeScript developers. Rather than giving you a thorough introduction to all aspects of TypeScript, we will focus in this part on the most common issues that arise when developing an Express backend or a React frontend with TypeScript. In addition to language features, we will also have a strong emphasis on tooling.

### Setting things up

Since version 22.6 that was released in August 2024, Node.js has been capable of running TypeScript code. Node doesn't actually understand TypeScript, it just deletes the type annotations and runs the remaining JavaScript.

Node.js doesn’t perform type checking, so you only get a small subset of TypeScript’s benefits out of the box. To unlock the full TypeScript experience, type checking, compilation, and richer tooling, we'll also need to install the [TypeScript](https://www.npmjs.com/package/typescript) npm package, which provides the compiler (tsc) and language services.

As we recall from [part 3](https://fullstackopen.com/en/part3), an npm project is set by running the command `npm init` in an empty directory. Then we can install the dependency by running

```bash
npm install --save-dev typescript
```

Let us also set up *scripts* within the file *package.json*:

```json
{
  // ...
  "type": "module",
  "scripts": {
   "tsc": "tsc --noEmit"
  },
  "devDependencies": {
    "typescript": "^5.9.3"
  }
}
```

We can now use the script to typecheck a TypeScript file:

```json
npm run tsc file.ts
```

The --noEmit option tells the TypeScript compiler not to generate JavaScript output. It runs type checking only, without generating compiled file.

Note that we have defined *"type": "module"* that tells Node.js to treat files in this package as ES modules (ESM) rather than CommonJS modules, meaning that we can use the *import/export *syntax instead of *require*, that is the preferred way in TypeScript.

Let us add a configuration file *tsconfig.json* to the project with the following content:

```json
{
  "compilerOptions":{
    "noImplicitAny": false,
    "noEmit": true
  }
}
```

The *tsconfig.json* file is used to define how the TypeScript compiler should interpret the code, how strictly the compiler should work, which files to watch or ignore, and [much more](https://www.typescriptlang.org/docs/handbook/tsconfig-json.html). For now, we will just disable the compiler option [noImplicitAny](https://www.typescriptlang.org/tsconfig#noImplicitAny), so it is not required to type for all variables used. We also defined ["noEmit": true](https://www.typescriptlang.org/tsconfig/#noEmit) since we are only going to be TypeScript compiler to checking.

We can now drop the parameter *--noEmit* from the npm script:

```json
{
  // ...
  "scripts": {
   "tsc": "tsc"
  },
  // ...
}
```

> JavaScript is a quite relaxed language in itself, and things can often be done in multiple different ways. For example, we have named vs anonymous functions, using const and let or var, and the optional use of *semicolons*. This part of the course differs from the rest by using semicolons. It is not a TypeScript-specific pattern but a general coding style decision taken when creating any kind of JavaScript project. Whether to use them or not is usually in the hands of the programmer, but since it is expected to adapt one's coding habits to the existing codebase, you are expected to use semicolons and adjust to the coding style in the exercises for this part. This part has some other coding style differences compared to the rest of the course as well, e.g. in the directory naming conventions.

#### A note about the coding style

JavaScript is a quite relaxed language in itself, and things can often be done in multiple different ways. For example, we have named vs anonymous functions, using const and let or var, and the optional use of *semicolons*. This part of the course differs from the rest by using semicolons. It is not a TypeScript-specific pattern but a general coding style decision taken when creating any kind of JavaScript project. Whether to use them or not is usually in the hands of the programmer, but since it is expected to adapt one's coding habits to the existing codebase, you are expected to use semicolons and adjust to the coding style in the exercises for this part. This part has some other coding style differences compared to the rest of the course as well, e.g. in the directory naming conventions.

Let's start by creating a simple Multiplier to the file *multiplier.ts*. It looks exactly as it would in JavaScript.

```typescript
const multiplicator = (a, b, printText) => {
  console.log(printText,  a * b);
}

multiplicator(2, 4, 'Multiplied numbers 2 and 4, the result is:');
```

As you can see, this is still ordinary basic JavaScript with no additional TS features. When we use the TypeScript compiler to do the type checking with the command `npm run tsc multiplier.ts` there are no complaints. So we know that the code is typesafe, and we can confidently run it with the command `node multiplier.ts`.

To speed things up, let’s create a script that first performs type checking and then runs the code if the checks pass.

```json
{
  // ..
  "scripts": {
    "tsc": "tsc",
    "multiply": "tsc && node multiplier.ts"
  },
  // ..
}
```

So now just `npm run multiply` typecheck and run the code.

What happens if we end up passing the wrong *types* of arguments to the multiplicator function?

Let's try it out!

```typescript
const multiplicator = (a, b, printText) => {
  console.log(printText,  a * b);
}

multiplicator('how about a string?', 4, 'Multiplied a string and 4, the result is:');
```

Now when we run the code, the output is: *Multiplied a string and 4, the result is: NaN*.

Wouldn't it be nice if the language itself could prevent us from ending up in situations like this? This is where we see the first benefits of TypeScript. Let's add types to the parameters and see where it takes us.

TypeScript natively supports multiple types including *number*, *string* and *Array*. See the comprehensive list [here](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html). More complex custom types can also be created.

The first two parameters of our function are of type number and the last one is of type string, both types are [primitives](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#the-primitives-string-number-and-boolean):

```typescript
const multiplicator = (a: number, b: number, printText: string) => {
  console.log(printText,  a * b);
}

multiplicator('how about a string?', 4, 'Multiplied a string and 4, the result is:');
```

Now the code is no longer valid TypeScript. When we try to run the code, we notice that it does not compile:

![VSCode terminal showing TypeScript compilation error: Argument of type string is not assignable to parameter of type number when calling multiplicator with a string as the first argument](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/K8zzOkX7GbMxyOeGrEG8Q6jP8XFYuF.png)

One of the best things about TypeScript's editor support is that you don't necessarily need to even run the code to see the issues. VSCode is so efficient that it informs you immediately when you are trying to use an incorrect type:

![VSCode editor showing inline type error with red squiggly underline under the string argument, with a tooltip displaying Argument of type string is not assignable to parameter of type number](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/YWWP1RVcdTS4QylT65eHKev3haXMZK.png)

### Creating your first own types

Let's expand our multiplicator into a slightly more versatile calculator that also supports addition and division. The calculator should accept three arguments: two numbers and the operation, either *multiply*, *add* or *divide*, which tells it what to do with the numbers.

In JavaScript, the code would require additional validation to make sure the last argument is indeed a string. TypeScript offers a way to define specific types for inputs, which describe exactly what type of input is acceptable. On top of that, TypeScript can also show the info on the accepted values already at the editor level.

We can create a *type* using the TypeScript native keyword *type*. Let's describe our type *Operation*:

```typescript
type Operation = 'multiply' | 'add' | 'divide';
```

Now the *Operation* type accepts only three kinds of values; exactly the three strings we wanted. Using the OR operator | we can define a variable to accept multiple values by creating a union type. In this case, we used exact strings (that, in technical terms, are called string literal types), but with unions, you could also make the compiler accept, for example, both string and number: *string | number*.

The *type* keyword defines a new name for a type: [a type alias](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#type-aliases). Since the defined type is a union of three possible values, it is handy to give it an alias that has a representative name.

Let's look at our calculator now:

```typescript
type Operation = 'multiply' | 'add' | 'divide';

const calculator = (a: number, b: number, op: Operation) => {
  if (op === 'multiply') {
    return a * b;
  } else if (op === 'add') {
    return a + b;
  } else if (op === 'divide') {
    if (b === 0) return 'can\'t divide by 0!';
    return a / b;
  }
}
```

Now, when we hover on top of the *Operation* type in the calculator function, we can immediately see suggestions on what to do with it:

![VSCode editor showing IntelliSense autocomplete suggestions when hovering over the Operation type parameter, displaying the three allowed values: multiply, add, and divide as clickable options](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/lxJujWBKfPqaNhKMoDjM8BBpasYEKk.png)

And if we try to use a value that is not within the *Operation* type, we get the familiar red warning signal and extra info from our editor:

![VSCode editor showing a red error squiggle under an invalid operation string value subtract, with a tooltip explaining Argument of type subtract is not assignable to parameter of type Operation](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/baQR6MQnw5BQPMwPRrk5xiV8vlr0D2.png)

This is already pretty nice, but one thing we haven't touched yet is typing the return value of a function. Usually, you want to know what a function returns, and it would be nice to have a guarantee that it returns what it says it does. Let's add a return value *number* to the calculator function:

```typescript
type Operation = 'multiply' | 'add' | 'divide';

const calculator = (a: number, b: number, op: Operation): number => {
  if (op === 'multiply') {
    return a * b;
  } else if (op === 'add') {
    return a + b;
  } else if (op === 'divide') {
    if (b === 0) return 'this cannot be done';
    return a / b;
  }
}
```

The compiler complains straight away because, in one case, the function returns a string. There are a couple of ways to fix this:

We could extend the return type to allow string values, like so:

```typescript
const calculator = (a: number, b: number, op: Operation): number | string =>  {
  // ...
}
```

Or we could create a return type, which includes both possible types, much like our Operation type:

```typescript
type Result = string | number;

const calculator = (a: number, b: number, op: Operation): Result =>  {
  // ...
}
```

But now the question is if it's *really* okay for the function to return a string?

When your code can end up in a situation where something is divided by 0, something has probably gone terribly wrong, and an error should be thrown and handled where the function was called. When you are deciding to return values you weren't originally expecting, the warnings you see from TypeScript prevent you from making rushed decisions and help you to keep your code working as expected.

One more thing to consider is that even though we have defined types for our parameters, the generated JavaScript used at runtime does not contain the type checks. So if, for example, the *Operation* parameter's value comes from an external interface, there is no definite guarantee that it will be one of the allowed values. Therefore, it's still better to include error handling and be prepared for the unexpected to happen. In this case, when there are multiple possible accepted values and all unexpected ones should result in an error, the [switch...case](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/switch) statement suits us better than if...else in our code.

The code of our calculator should look something like this:

```typescript
type Operation = 'multiply' | 'add' | 'divide';

const calculator = (a: number, b: number, op: Operation) : number => {
  switch(op) {
    case 'multiply':
      return a * b;
    case 'divide':
      if (b === 0) throw new Error('Can\'t divide by 0!');
      return a / b;
    case 'add':
      return a + b;
    default:
      throw new Error('Operation is not multiply, add or divide!');
  }
}

try {
  console.log(calculator(1, 5 , 'divide'));
} catch (error: unknown) {
  let errorMessage = 'Something went wrong: '
  if (error instanceof Error) {
    errorMessage += error.message;
  }
  console.log(errorMessage);
}
```

### Type narrowing

The default type of the catch block parameter *error* is *unknown*. The [unknown](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-0.html#new-unknown-top-type) is a kind of top type that was introduced in TypeScript version 3 to be the type-safe counterpart of *any*. Anything is assignable to *unknown*, but *unknown* isn’t assignable to anything but itself and *any* without a type assertion or a control flow-based type narrowing. Likewise, no operations are permitted on an *unknown* without first asserting or narrowing it to a more specific type.

Both the possible causes of exception (wrong operator or division by zero) will throw an [Error](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error) object with an error message, that our program prints to the user.

If our code would be JavaScript, we could print the error message by just referring to the field [message](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/message) of the object *error* as follows:

```typescript
try {
  console.log(calculator(1, 5 , 'divide'));
} catch (error) {
  console.log('Something went wrong: ' + error.message);
}
```

Since the default type of the *error* object in TypeScript is *unknown*, we have to [narrow](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) the type to access the field:

```typescript
try {
  console.log(calculator(1, 5 , 'divide'));
} catch (error: unknown) {
  let errorMessage = 'Something went wrong: '
  // here we can not use error.message
  if (error instanceof Error) {    
   // the type is narrowed and we can refer to error.message   
    errorMessage += error.message;  
}
  // here we can not use error.message

  console.log(errorMessage);
}
```

Here, the narrowing was done with the instanceof type guard, which is just one of the many ways to narrow a type. We shall see many others later in this part.

### Accessing command line arguments

The programs we have written are alright, but it sure would be better if we could use command-line arguments instead of always having to change the code to calculate different things.

Let's try it out, as we would in a regular Node application, by accessing *process.argv*. However, something is not right:

![VSCode editor showing a TypeScript error under process.argv with the message Cannot find name process. Do you need to install type definitions for node? Try npm i --save-dev @types/node](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/mR9IFl9g7ltPrJ9mqRTzesdlEDV5ma.png)

The error message gives us a hint how to fix the problem:

```bash
npm install --save-dev @types/node
```

When the package *@types/node* is installed, the compiler does not complain about the variable process. Note that there is no need to require the types in the code, the installation of the package is enough!

### About @types/{npm_package}

We just installed the npm package *@types/node *to get rid of a typing error. What actually is this package?

TypeScript expects types for all code you use, including external libraries, so it can provide IntelliSense, editor support, and compile-time checks. Many libraries don’t include their own types. When that happens, the community-maintained typings from [DefinitelyTyped](https://github.com/DefinitelyTyped/DefinitelyTyped) are published on npm under the @types organization.

Install @types packages only if the library doesn’t already ship types. You can check the package’s documentation or package.json for a types field. Install these packages as *devDependencies*, since they’re only needed during development and build, and keep their versions aligned with the library to avoid mismatches.

For example, *@types/express* adds types for Request, Response, Router, and middleware, improving safety and ergonomics when building routes. Similarly, you can install types for other libraries that lack built-in types, such as *@types/react*, *@types/lodash,* or *@types/mongoose*.

Behind these packages is the [DefinitelyTyped](https://github.com/DefinitelyTyped/DefinitelyTyped) project, an active community that maintains and updates typings for a vast number of npm libraries. In most cases, you can rely on these instead of writing your own. The takeaway: prefer built-in types when available; otherwise, install the relevant @types packages as devDependencies and keep them in sync with your library versions.

### Improving the project

We can get the *multiplier* to work with command-line parameters as follows:

```typescript
const multiplicator = (a: number, b: number, printText: string) => {
  console.log(printText,  a * b);
}

// command line arguments start from process.argv[2]
const a: number = Number(process.argv[2])
const b: number = Number(process.argv[3])

multiplicator(a, b, `Multiplied ${a} and ${b}, the result is:`);
```

And we can run it with:

```bash
npm run multiply 5 2
```

If the program is run with parameters that are not of the right type, e.g.

```bash
npm run multiply 5 lol
```

it "works" but gives us the answer:

```typescript
Multiplied 5 and NaN, the result is: NaN
```

The reason for this is, that *Number('lol')* returns *NaN*, which is actually of type *number*, so TypeScript has no power to rescue us from this kind of situation.

To prevent this kind of behavior, we have to validate the data given to us from the command line.

The improved version of the multiplicator looks like this:

```typescript
interface MultiplyValues {
  value1: number;
  value2: number;
}

const parseArguments = (args: string[]): MultiplyValues => {
  if (args.length < 4) throw new Error('Not enough arguments');
  if (args.length > 4) throw new Error('Too many arguments');

  if (!isNaN(Number(args[2])) && !isNaN(Number(args[3]))) {
    return {
      value1: Number(args[2]),
      value2: Number(args[3])
    }
  } else {
    throw new Error('Provided values were not numbers!');
  }
}

const multiplicator = (a: number, b: number, printText: string) => {
  console.log(printText,  a * b);
}

try {
  const { value1, value2 } = parseArguments(process.argv);
  multiplicator(value1, value2, `Multiplied ${value1} and ${value2}, the result is:`);
} catch (error: unknown) {
  let errorMessage = 'Something bad happened.'
  if (error instanceof Error) {
    errorMessage += ' Error: ' + error.message;
  }
  console.log(errorMessage);
}
```

When we now run the program:

```bash
npm run multiply 1 lol
```

we get a proper error message:

```text
Something bad happened. Error: Provided values were not numbers!
```

There is quite a lot going on in the code. The most important addition is the function *parseArguments* which ensures that the parameters given to *multiplicator* are of the right type. If not, an exception is thrown with a descriptive error message.

The definition of the function has a couple of interesting things:

```typescript
const parseArguments = (args: string[]): MultiplyValues => {
  // ...
}
```

Firstly, the parameter *args* is an [array](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#arrays) of strings.

The return value of the function has the type *MultiplyValues*, which is defined as follows:

```typescript
interface MultiplyValues {
  value1: number;
  value2: number;
}
```

The definition utilizes TypeScript's [Interface](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#interfaces) keyword, which is one way to define the "shape" an object should have. In our case, it is quite obvious that the return value should be an object with the two properties *value1* and *value2*, which should both be of type number.

#### The alternative array syntax

Note that there is also an alternative syntax for [arrays](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#arrays) in TypeScript. Instead of writing

```typescript
let values: number[];
```

we could use the "generics syntax" and write

```bash
let values: Array<number>;
```

In this course we shall mostly be following the convention enforced by the Eslint rule [array-simple](https://typescript-eslint.io/rules/array-type/#array-simple) that suggests writing the simple arrays with the [] syntax and using the <> syntax for the more complex ones, see [here](https://typescript-eslint.io/rules/array-type/#array-simple) for examples.

### Exercise: 1. Body mass index

##### Submission repository

For the exercises of this part, you should create a new repository, inside of which you copy the contents of this repository [https://github.com/fullstack-hy2020/fs-typescript](https://github.com/fullstack-hy2020/fs-typescript)

All of the repository content (except the directory *.git*) must be copied to the root directory of your repository. So the content of your submission repository root should be **exactly** the below until you can start:

```text
.git 
.github
.gitignore
flightdiaries
healthapp
healthapp-tests
patientor
patientor-api-tests
patientor-tests
```

##### Setup

Start by setting up the node project that will be used in ihis and the next 6 exercises:

- Initialize a new Node.js project inside the directory named *healtapp* by running *npm init*
- Install the development dependency *typescript*
- In the *healthapp* directory, create a *tsconfig.json* file with the following contents:

```json
{
  "compilerOptions": {
    "noImplicitAny": true,
    "noEmit": true
  }
}
```

The compiler option [noImplicitAny](https://www.typescriptlang.org/tsconfig#noImplicitAny) makes it mandatory to have types for all variables used. This option is currently a default, but it lets us define it explicitly.

Remember also set *"type": "module"* in the file *package.json*:

```json
{
  type: "module",
  // ...
}
```

##### The bmi calculator

Create the code of this exercise in the file *bmiCalculator.ts*.

Write a function *calculateBmi* that calculates a [BMI](https://en.wikipedia.org/wiki/Body_mass_index) based on a given height (in centimeters) and weight (in kilograms) and then returns a message that suits the results.

Call the function in the same file with hard-coded parameters and print out the result. The code

```bash
console.log(calculateBmi(180, 74))
```

should print the following message:

```typescript
Normal range
```

The message content is defined based on the BMI [wikipedia](https://en.wikipedia.org/wiki/Body_mass_index) page.

Create a script for typechecking and running the program with the command `npm run calculateBmi.`

### Exercise: 2. Exercise calculator

Create the code of this exercise in file *exerciseCalculator.ts* in the same project with the previous exercise.

Write a function *calculateExercises* that calculates the average time of *daily exercise hours*, compares it to the *target amount* of daily hours and returns an object that includes the following values:

- the number of days
- the number of training days
- the original target value
- the calculated average time
- boolean value describing if the target was reached
- a rating between the numbers 1-3 that tells how well the hours are met. You can decide on the metric on your own.
- a text value explaining the rating, you can come up with the explanations

The daily exercise hours are given to the function as an [array](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#arrays) that contains the number of exercise hours for each day in the training period. Eg. a week with 3 hours of training on Monday, none on Tuesday, 2 hours on Wednesday, 4.5 hours on Thursday and so on would be represented by the following array:

```typescript
[3, 0, 2, 4.5, 0, 3, 1]
```

For the Result object, you should create an [interface](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#interfaces).

If you call the function with parameters *[3, 0, 2, 4.5, 0, 3, 1]* and *2*, it should return:

```bash
{ 
  periodLength: 7,
  trainingDays: 5,
  success: false,
  rating: 2,
  ratingDescription: 'not too bad but could be better',
  target: 2,
  average: 1.9285714285714286
}
```

Create an npm script, `npm run calculateExercises`, to call the function with hard-coded values.

### Exercise: 3. Command line

Change the previous exercises so that you can give the parameters of *bmiCalculator* and *exerciseCalculator* as command-line arguments.

Your program could work eg. as follows:

```bash
$ npm run calculateBmi 180 91

Overweight
```

and:

```bash
$ npm run calculateExercises 2 1 0 2 4.5 0 3 1 0 4

{
  periodLength: 9,
  trainingDays: 6,
  success: false,
  rating: 2,
  ratingDescription: 'not too bad but could be better',
  target: 2,
  average: 1.7222222222222223
}
```

In the example, the *first argument* is the target value.

Handle exceptions and errors appropriately. The *exerciseCalculator* should accept inputs of varied lengths. Determine by yourself how you manage to collect all needed input.

A thing to notice: if you define helper functions in other modules, you should use the JavaScript module system, that is, the one we have used with React, where importing is done with

```typescript
import { isNotNumber } from "./utils.ts";
```

and exporting

```typescript
export const isNotNumber = (argument: any): boolean =>
  isNaN(Number(argument));

export default "this is the default..."
```

### Adding Express to the mix

Right now, we are in a pretty good place. Our project is set up, and we have two executable calculators in it. However, since we aim to learn Full Stack development, it is time to start working with some HTTP requests.

Before that, let us expand a bit our configuration in the file [tsconfig.json](https://www.typescriptlang.org/docs/handbook/tsconfig-json.html), which so far has only one tsconfig rule [noImplicitAny](https://www.typescriptlang.org/tsconfig#noImplicitAny). Change the file to have the following content:

```json
{
  "compilerOptions": {
    "target": "esnext",
    "noEmit": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "module": "nodenext",
    "esModuleInterop": true,
    "allowImportingTsExtensions": true
  }
}
```

Do not worry yet too much about the *compilerOptions*, they will be under closer inspection later on.

If you want, you can find explanations for each of the configurations from the TypeScript documentation, from the really handy [tsconfig page](https://www.typescriptlang.org/tsconfig), or from the tsconfig [schema definition](http://json.schemastore.org/tsconfig).

Let us start the coding by installing Express:

```bash
npm install express
```

and then add the *start* script to package.json:

```json
{
  // ...
  "scripts": {
    "tsc": "tsc",
    "multiply": "tsc  && node multiplier.ts",
    "start": "tsc && node index.ts"
  },
  // ..
}
```

Now we can create the file *index.ts*, and write the HTTP GET *ping* endpoint to it:

```javascript
const express = require('express');
const app = express();

app.get('/ping', (req, res) => {
  res.send('pong');
});

const PORT = 3003;

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

Everything else seems to be ok but, as you'd expect, the *req* and *res* parameters of *app.get* need typing.

If you look carefully, VSCode is also complaining about the importing of Express. You can see a short yellow line of dots under *require*. Let's hover over the problem:

![VSCode editor showing a yellow dotted underline under the require keyword with a tooltip stating require call may be converted to an import. Quick fix: Convert to ES6 module](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/ONnFmSXkDlk54PoThghGYzBT09A23y.png)

The complaint is that the *'require' call may be converted to an import*. Let us follow the advice and write the import as follows:

```typescript
import express from 'express';
```

> VSCode offers you the possibility to fix the issues automatically by clicking the *Quick Fix...* button. Keep your eyes open for these helpers/quick fixes; listening to your editor usually makes your code better and easier to read. The automatic fixes for issues can be a major time saver as well.

VSCode offers you the possibility to fix the issues automatically by clicking the *Quick Fix...* button. Keep your eyes open for these helpers/quick fixes; listening to your editor usually makes your code better and easier to read. The automatic fixes for issues can be a major time saver as well.

Import syntax is the way to go with TypeScript so we shall from this point on stick to it!

Now we run into another problem: the compiler complains about the import statement. Once again, the editor is our best friend when trying to find out what the issue is:

![VSCode editor showing a red error underline under the Express import statement with the message Cannot find module express or its corresponding type declarations](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/GZwFt0cteRFGSKpu53yWTasBq23G2m.png)

The reason for the error is that we haven't installed types for *Express*. Let's do what the suggestion says and run:

```bash
npm install --save-dev @types/express
```

There should not be any errors remaining. Note that you may need to reopen the file in the editor to get VS Code in sync.

There is one more problem with the code:

![VSCode editor showing unused parameter warnings for req and res in the app.get callback, with squiggly lines under the unused variables](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/OyDjrNwPyrGHfJ0yn5edQHHy5lMSqA.png)

This is because we banned unused parameters in our *tsconfig.json*:

```json
{
  "compilerOptions": {
    "target": "esnext",
    "noEmit": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "module": "nodenext",
    "esModuleInterop": true,
    "allowImportingTsExtensions": true
  }
}
```

This configuration might create problems if you have library-wide predefined functions that require declaring a variable even if it's not used at all, as is the case here. Fortunately, this issue has already been solved on the configuration level. Once again, hovering over the issue gives us a solution. This time, we can just click the quick fix button:

![VSCode quick fix menu showing the option to prefix unused variable with underscore, offering to rename req to _req](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/YnFPv4UlS1XLtZVqzKTG6oIpCgX1uS.png)

If it is absolutely impossible to get rid of an unused variable, you can prefix it with an underscore to inform the compiler you have thought about it and there is nothing you can do.

Let's rename the *req* variable to *_req*.

Finally, we are ready to start the application. It seems to work fine:

![Terminal output showing the Express server starting successfully with the message Server running on port 3003](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/9V5fJrNxnUsAciEiU54OSodSlIambP.png)

To streamline development, we should enable auto-reloading. You’ve already used *node --watch *in this course,

We could try the following:

```json
{
  // ...
  "scripts": {
      // ...
      "dev": "tsc && node --watch index.ts",  
  },
  // ...
}
```

However, this does not quite work. The typecheck is done only at the beginning. One solution would be to run the type checking and Node in watch mode concurrently. This is easy with the npm package [concurrently](https://www.npmjs.com/package/concurrently). Let us install it:

```bash
npm install --save-dev concurrently
```

Add a script to *package.json*:

```bash
  "scripts": {
    "tsc": "tsc",
    "multiply": "tsc && node multiplier.ts",
    "calculate": "tsc && node calculator.ts",
    "start": "node index.ts",
    "dev": "concurrently \"tsc --watch\" \"node --watch index.ts\""
  },
```

The `npm start` is now simplified, it is assumed that the type checking is done *before* running the code.

And now, by running `npm run dev,` we have a working, auto-reloading development environment for our project! There is, however, one thing to note. If a type error is introduced into the program, the type checker notices it, but the app keeps running, so you need to keep an eye on what happens in the console:

![Terminal showing TypeScript compilation errors in the concurrently watch output, with tsc reporting type errors while the Node server continues running](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/cbTMBZZIRyc9G3IsSG0xT7VdXaHgyr.png)

There are also setups that would stop the program from running in case of a type error. We prefer a more lightweight approach.

The current trend is pretty much to rely on the editor for type checking while writing code, and run `tsc --noEmit` in a [continuous integration](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-continuous-integration)pipeline or as a Git [pre-commit](https://pre-commit.com/) hook. This keeps the dev loop lightweight. `node --watch src/index.ts` just runs your code on save, while the editor surfaces type errors in real time. Type safety is still enforced, just at the moments that matter rather than blocking every run.

### Exercise: 4. Express

We will continue to build the app of the previous exercises.

Add now Express to the app dependencies and create an HTTP GET endpoint *hello* that answers 'Hello Full Stack!'

The web app should be started with the commands `npm start` in production mode and *`npm run dev `*in development mode.

Replace also your existing *tsconfig.json* file with the following content:

```json
{
  "compilerOptions": {
    "target": "esnext",
    "noEmit": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "module": "nodenext",
    "esModuleInterop": true,
    "allowImportingTsExtensions": true
  }
}
```

Make sure there aren't any errors!

### Exercise: 5. WebBmi

Add an endpoint for the BMI calculator that can be used by doing an HTTP GET request to the endpoint *bmi* and specifying the input with [query string parameters](https://en.wikipedia.org/wiki/Query_string). For example, to get the BMI of a person with a height of 180 and a weight of 72, the URL is [http://localhost:3003/bmi?height=180&weight=72](http://localhost:3003/bmi?height=180&weight=72).

The response is a JSON of the form:

```json
{
  weight: 72,
  height: 180,
  bmi: "Normal range"
}
```

See the [Express documentation](https://expressjs.com/en/5x/api.html#req.query) for info on how to access the query parameters.

If the query parameters of the request are of the wrong type or missing, a response with proper status code and an error message is given:

```json
{
  error: "malformatted parameters"
}
```

Do not copy the calculator code to file *index.ts*; instead, make it a [TypeScript module](https://www.typescriptlang.org/docs/handbook/modules.html) that can be imported into *index.ts*.

Consider adding the condition *process.argv[1] === import.meta.filename *to the file *bmiCalculator.ts*. It tests whether the module is main, i.e. it is run directly from the command line (in our case, `npm run calculateBmi`), or it is used by other modules that import functions from it (e.g. index.ts). Parsing command-line arguments makes sense only if the module is main. Without this condition, you might see argument validation errors when starting the application via `npm start` or `npm run dev`:

```typescript
if (process.argv[1] === import.meta.filename) {
  // do not run this code if module is imported
}
```

### The horrors of any

Now that we have our first endpoints completed, you might notice that we have used barely any TypeScript in these small examples. When examining the code a bit closer, we can see a few dangers lurking there.

Let's add the HTTP POST endpoint *calculate* to our app:

```javascript
import { calculator } from './calculator.ts';

app.use(express.json());

// ...

app.post('/calculate', (req, res) => {
  const { value1, value2, op } = req.body;

  const result = calculator(value1, value2, op);
  return res.send({ result });
});
```

To get this working, we must add an *export* to the function *calculator*:

```typescript
export const calculator = (a: number, b: number, op: Operation) : number => {
```

When you hover over the *calculate* function, you can see the typing of the *calculator* even though the code itself does not contain any typing:

![VSCode editor showing type information tooltip when hovering over the calculator function, displaying the function signature with typed parameters: (a: number, b: number, op: Operation) => number](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/aQdzXxRzqNmbmwvyo528U7ESBDHdxY.png)

But if you hover over the values parsed from the request, an issue arises:

![VSCode editor showing that variables destructured from req.body have the type any, with tooltips indicating const value1: any, const value2: any, const op: any](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/GWEjPOhrtBe0va9IIvBIEpmu0QzCVX.png)

All of the variables have the type *any*. It is not all that surprising, as no one has given them a type yet. There are a couple of ways to fix this, but first, we have to consider why this is accepted and where the type *any* came from.

In TypeScript, every untyped variable whose type cannot be inferred implicitly becomes of type [any](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#any). Any is a kind of "wild card" type, which stands for *whatever* type. Things become implicitly any type quite often when one forgets to type functions.

We can also explicitly type things *any*. The only difference between the implicit and explicit any type is how the code looks; the compiler does not care about the difference.

Programmers however see the code differently when *any* is explicitly enforced than when it is implicitly inferred. Implicit *any* typings are usually considered problematic since it is quite often due to the coder forgetting to assign types (or being too lazy to do it), and it also means that the full power of TypeScript is not properly exploited.

This is why the configuration rule [noImplicitAny](https://www.typescriptlang.org/tsconfig#noImplicitAny) exists on the compiler level, and it is highly recommended to keep it on at all times. In the rare occasions when you truly cannot know what the type of a variable is, you should explicitly state that in the code:

```typescript
const a : any = /* no clue what the type will be! */.
```

We already have *noImplicitAny: true* configured in our example, so why does the compiler not complain about the implicit *any* types? The reason is that the *body* field of an Express [Request](https://expressjs.com/en/5x/api.html#req) object is explicitly typed *any*. The same is true for the *request.query* field that Express uses for the query parameters.

> **A note on importing**
> 
> If you looked closely to the code, you propably noticed that the import uses the full filename including the extension:
> 
> This is because Node.js needs to distinguish between the *.ts* source file and a potential compiled *.js* file of the same name, despite we will in our case not even have the *.js* files.
> 
> ```typescript
> import { calculator } from './calculator.ts';
> ```

**A note on importing**

If you looked closely to the code, you propably noticed that the import uses the full filename including the extension:

```typescript
import { calculator } from './calculator.ts';
```

This is because Node.js needs to distinguish between the *.ts* source file and a potential compiled *.js* file of the same name, despite we will in our case not even have the *.js* files.

What if we would like to restrict developers from using the *any* type? Fortunately, we have methods other than *tsconfig.json* to enforce a coding style. What we can do is use *ESlint* to manage our code. Let's install ESlint and its TypeScript extensions:

```bash
npm install --save-dev eslint @eslint/js typescript-eslint
```

> **NOTE:** at the time of writing this (28.3.2026), the most recent [typescript-eslint](https://www.npmjs.com/package/typescript-eslint) version (5.57.2) is not compatible with TypeScript 6, which was released 23.3.2026. Due to this, the command `npm install` fails. Until a new version is released, you must run the command in the form `npm install --legacy-peer-deps`

**NOTE:** at the time of writing this (28.3.2026), the most recent [typescript-eslint](https://www.npmjs.com/package/typescript-eslint) version (5.57.2) is not compatible with TypeScript 6, which was released 23.3.2026. Due to this, the command `npm install` fails. Until a new version is released, you must run the command in the form `npm install --legacy-peer-deps`

We will configure ESlint to [disallow explicit any](https://github.com/typescript-eslint/typescript-eslint/blob/main/packages/eslint-plugin/docs/rules/no-explicit-any.mdx). Write the following rules to *eslint.config.mjs*:

```javascript
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config({
  files: ['**/*.ts'],
  extends: [
    eslint.configs.recommended,
    ...tseslint.configs.recommendedTypeChecked,
  ],
  languageOptions: {
    parserOptions: {
      project: true,
      tsconfigRootDir: import.meta.dirname,
    },
  },
  rules: {
    '@typescript-eslint/no-explicit-any': 'error',
  },
});
```

Let us also set up a *lint* npm script to inspect the files by modifying the *package.json* file:

```json
{
  // ...
  "scripts": {
      "tsc": "tsc",
      "calculate": "tsc && node calculator.ts",
      "multiply": "tsc && node multiplier.ts",
      "start": "node index.ts",
      "dev": "concurrently \"tsc --watch\" \"node --watch index.ts\"",
      "lint": "eslint ."
      //  ...
  },
  // ...
}
```

Now lint will complain if we try to define a variable of type *any*:

![ESLint error in VSCode terminal or problems panel showing @typescript-eslint/no-explicit-any rule violation when using the any type explicitly](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/VWAb0b1xohk2XP0Kw5EWLFuVF6tj5S.png)

typescript-eslint has a lot of TypeScript-specific ESLint rules, but you can also use all basic ESLint rules in TypeScript projects. For now, we should probably go mostly with the recommended settings, and we will modify the rules as we go along whenever we find something we want to change the behavior of.

On top of the recommended settings, we should try to get familiar with the coding style required in this part and *set the semicolon at the end of each line of code to be required*. For that, we should install and configure [@stylistic/eslint-plugin](https://eslint.style/packages/default):

```bash
npm install --save-dev @stylistic/eslint-plugin
```

Our final *eslint.config.mjs* looks as follows:

```javascript
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import stylistic from "@stylistic/eslint-plugin";

export default tseslint.config({
  files: ['**/*.ts'],
  extends: [
    eslint.configs.recommended,
    ...tseslint.configs.recommendedTypeChecked,
  ],
  languageOptions: {
    parserOptions: {
      project: true,
      tsconfigRootDir: import.meta.dirname,
    },
  },
  plugins: {
    "@stylistic": stylistic,
  },
  rules: {
    '@stylistic/semi': 'error',
    '@typescript-eslint/no-unsafe-assignment': 'error',
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'off',
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/restrict-template-expressions': 'off',
    '@typescript-eslint/restrict-plus-operands': 'off',
    '@typescript-eslint/no-unused-vars': [
      'error',
      { 'argsIgnorePattern': '^_' }
    ],
  },
});
```

Quite a few semicolons are missing, but those are easy to add. We also have to solve the ESLint issues concerning *any* type:

![VSCode editor showing ESLint warnings about missing semicolons at the end of code lines, with yellow squiggly underlines](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/kdlaX1UdmJifhecjBgAe8b8PuVIjPR.png)

We could and probably should disable some ESlint rules to get the data from the request body.

Disabling *@typescript-eslint/no-unsafe-assignment* for the destructuring assignment and calling the [Number](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/Number) constructor to values is nearly enough:

```typescript
app.post('/calculate', (req, res) => {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment 
  const { value1, value2, op } = req.body;

  const result = calculator(Number(value1), Number(value2), op);
  return res.send({ result });
});
```

However this still leaves one problem to deal with, the last parameter in the function call is not safe:

![VSCode editor showing an ESLint error @typescript-eslint/no-unsafe-argument for passing an any typed variable as an argument to the calculator function](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/jYuOvA2BAtgSq2qRPcHpPcol1q7b2d.png)

We can just disable another ESlint rule to get rid of that:

```typescript
app.post('/calculate', (req, res) => {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  const { value1, value2, op } = req.body;

  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument 
  const result = calculator(Number(value1), Number(value2), op);
  return res.send({ result });
});
```

We now have ESlint silenced but we are totally at the mercy of the user. We most definitively should do some validation to the post data and give a proper error message if the data is invalid:

```typescript
app.post('/calculate', (req, res) => {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  const { value1, value2, op } = req.body;

  if ( !value1 || isNaN(Number(value1)) ) {    
     return res.status(400).send({ error: '...'});  
  }
  // more validations here...

  // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
  const result = calculator(Number(value1), Number(value2), op);
  return res.send({ result });
});
```

We shall see later in this part some techniques on how the *any* typed data (eg. the input an app receives from the user) can be *narrowed* to a more specific type (such as number). With a proper narrowing of types, there is no more need to silence the ESlint rules.

> **Warning**
> 
> Quite often VS code loses track of what is really happening in the code and it shows type or style related warnings despite the code having been fixed. If this happens (to me it has happened quite often), close and open the file that is giving you trouble or just restart the editor. It is also good to doublecheck that everything really works by running the compiler and the ESlint from the command line with commands:
> 
> When run in command line you get the "real result" for sure. So, never trust the editor too much!
> 
> ```bash
> npm run tsc
> npm run lint
> ```

**Warning**

Quite often VS code loses track of what is really happening in the code and it shows type or style related warnings despite the code having been fixed. If this happens (to me it has happened quite often), close and open the file that is giving you trouble or just restart the editor. It is also good to doublecheck that everything really works by running the compiler and the ESlint from the command line with commands:

```bash
npm run tsc
npm run lint
```

When run in command line you get the "real result" for sure. So, never trust the editor too much!

### Type assertion

Using a [type assertion](https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#type-assertions) is another "dirty trick" that can be done to keep TypeScript compiler and Eslint quiet. Let us export the type Operation in *calculator.ts*:

```bash
export type Operation = 'multiply' | 'add' | 'divide';
```

Now we can import the type and use the type assertion *as* to tell the TypeScript compiler what type a variable has:

```typescript
import { calculator, type Operation } from './calculator';
// ...

app.post('/calculate', (req: Request, res: Response) => {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  const { value1, value2, op } = req.body;

  if ( !value1 || isNaN(Number(value1)) ) {    
     return res.status(400).send({ error: '...'});  
  }

  const operation = op as Operation;
  const result = calculator(Number(value1), Number(value2), operation);
  return res.send({ result });
});
```

> Note that we imported the type Operation with using the *type* keyword:
> 
> This is required because we're running the code directly with Node.js, which strips TypeScript types at runtime, so any type-only imports must be explicitly marked as such.
> 
> ```typescript
> import { calculator, type Operation } from './calculator';
> ```

Note that we imported the type Operation with using the *type* keyword:

```typescript
import { calculator, type Operation } from './calculator';
```

This is required because we're running the code directly with Node.js, which strips TypeScript types at runtime, so any type-only imports must be explicitly marked as such.

The defined constant *operation* now has the type Operation, and the compiler is perfectly happy, no quieting of the Eslint rule is needed on the following function call. The new variable is actually not needed, the type assertion can be done when an argument is passed to the function:

```javascript
app.post('/calculate', (req: Request, res: Response) => {
  // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
  const { value1, value2, op } = req.body;

  // validate the data here

  const result = calculator(Number(value1), Number(value2), op as Operation);

  return res.send({ result });
});
```

Using a type assertion (or quieting an ESLint rule) is always a bit risky. It leaves the TypeScript compiler off the hook, the compiler just trusts that we, as developers, know what we are doing. If the asserted type *does not* have the right kind of value, the result will be a runtime error, so one must be pretty careful when validating the data if a type assertion is used.

In the next chapter, we shall have a look at [type narrowing](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) which will provide a much more safe way of giving a stricter type for data that is coming from an external source.

### Exercise: 6. Eslint

Configure your project to use the above ESLint settings and fix all the warnings.

**NOTE:** at the time of writing this (28.3.2026), the most recent [typescript-eslint](https://www.npmjs.com/package/typescript-eslint) version (5.57.2) is not compatible with TypeScript 6, which was released 23.3.2026. Due to this, the command `npm install` fails. Until a new version is released, you must run the command in the form `npm install --legacy-peer-deps`

### Exercise: 7. WebExercises

Add an endpoint to your app for the exercise calculator. It should be used by doing a HTTP POST request to the endpoint [http://localhost:3000/exercises](http://localhost:3000/exercises) with the following input in the request body:

```json
{
  "daily_exercises": [1, 0, 2, 0, 3, 0, 2.5],
  "target": 2.5
}
```

The response is a JSON of the following form:

```json
{
    "periodLength": 7,
    "trainingDays": 4,
    "success": false,
    "rating": 1,
    "ratingDescription": "bad",
    "target": 2.5,
    "average": 1.2142857142857142
}
```

If the body of the request is not in the right form, a response with the proper status code and an error message are given. The error message is either

```json
{
  error: "parameters missing"
}
```

or

```json
{
  error: "malformatted parameters"
}
```

depending on the error. The latter happens if the input values do not have the right type, i.e. they are not numbers or convertible to numbers.

In this exercise, you might find it beneficial to use the *explicit any* type when handling the data in the request body. Our ESlint configuration is preventing this but you may unset this rule for a particular line by inserting the following comment as the previous line:

```typescript
// eslint-disable-next-line @typescript-eslint/no-explicit-any
```

You might also get in trouble with rules *no-unsafe-member-access*, *no-unsafe-assignment,* and *no-unsafe-call*. These rules may be ignored in this exercise.

Note that you need to have a correct setup to get the request body; see [part 3](https://fullstackopen.com/en/part3/node_js_and_express#receiving-data).

### Exercise: 8. Checkup

The repository that you copied for the exercises contains a set of tests for the healthapp.

Ensure first that the tests work locally:

- Start the app with `npm start`
- It is assumed that the healtapp runs in port 3000
- Open a new terminal and go to directory *healthapp-tests*
- Before the first time you run tests, run the following commands `npm install` `npx playwright install`
- Run tests with command `npm test`
- Make sure that the app has started before running the tests!

When tests work locally, change the start of the file .*github/workflows/healthapp-e2e-tests.yml* as follows:

```yaml
name: Health app E2E Tests

on:
  push:
    branches: [ main, master ]
```

Push the code to GitHub and ensure tests pass also there

![GitHub Actions workflow run showing successful completion of Health app E2E Tests with all checks passing, green checkmark indicators visible](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/pWsWOl1JHS88HCGSJGizaLAcxYVHXh.png)