chapter 6

# Grande finale: Patientor

<details>
<summary>Exercises in this chapter</summary>

Note: You will not receive points for exercises in this chapter until you lock the chapter and a teacher reviews your answers.

1. 23. Patientor, step 1
2. 24. Patientor, step 2
3. 25. Patientor, step 3
4. 26. Patientor, step 4
5. 27. Patientor, step 5
6. 28. Patientor, step 6
7. 29. Patientor, step 7
8. 30. Patientor, step 8
9. 31. Patientor, step 9
10. 32. Patientor, step 10
11. 33. Patientor, the final check
12. 34. Your GitHub repository

</details>

### Working with an existing codebase

When diving into an existing codebase for the first time, it is good to get an overall view of the conventions and structure of the project. You can start your research by reading the *README.md* in the root of the repository. Usually, the README contains a brief description of the application and the requirements for using it, as well as how to start it for development. If the README is not available or someone has "saved time" and left it as a stub, you can take a peek at the *package.json*. It is always a good idea to start the application and click around to verify you have a functional development environment.

You can also browse the folder structure to get some insight into the application's functionality and/or the architecture used. These are not always clear, and the developers might have chosen a way to organize code that is not familiar to you. The [sample project (opens in a new tab)](https://github.com/fullstack-hy2020/fs-typescript/tree/main/patientor/frontend) used in the rest of this part is organized, feature-wise. You can see what pages the application has, and some general components, e.g., modals and state. Keep in mind that the features may have different scopes. For example, modals are visible UI-level components, whereas the state is comparable to business logic and keeps the data organized under the hood for the rest of the app to use.

TypeScript provides types for what kind of data structures, functions, components, and state to expect. You can try looking for *types.ts* or something similar to get started. VSCode is a big help, and simply highlighting variables and parameters can provide quite a lot of insight. All this naturally depends on how types are used in the project.

If the project has unit, integration, or end-to-end tests, reading those is most likely beneficial. Test cases are your most important tool when refactoring or adding new features to the application. You want to make sure not to break any existing features when hammering around the code. TypeScript can also give you guidance with argument and return types when changing the code.

Remember that reading code is a skill in itself, so don't worry if you don't understand the code on your first read-through. The code may have a lot of corner cases, and pieces of logic may have been added here and there throughout its development cycle. It is hard to imagine what kind of problems the previous developer has wrestled with. Think of it all like [growth rings in trees (opens in a new tab)](https://en.wikipedia.org/wiki/Dendrochronology#Growth_rings). Understanding everything requires digging deep into the code and business domain requirements. The more code you read, the better you will be at understanding it. You will most likely read far more code than you are going to produce throughout your life.

### Patientor frontend

It's time to get our hands dirty finalizing the frontend for the backend we built in Exercises [9-16 (opens in a new tab)](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-4). We will actually also need to add some new features to the backend for finishing the app.

Before diving into the code, let us start both the frontend and the backend.

If all goes well, you should see a patient listing page. It fetches a list of patients from our backend, and renders it to the screen as a simple table. There is also a button for creating new patients on the backend. As we are using mock data instead of a database, the data will not persist - closing the backend will delete all the data we have added. UI design has not been a strong point of the creators, so let's disregard the UI for now.

After verifying that everything works, we can start studying the code. All the interesting stuff resides in the *src* folder. For your convenience, there is already a *types.ts* file for basic types used in the app, which you will have to extend or refactor in the exercises.

In principle, we could use the same types for both the backend and the frontend, but usually, the frontend has different data structures and use cases for the data, which causes the types to be different. For example, the frontend has a state and may want to keep data in objects or maps whereas the backend uses an array. The frontend might also not need all the fields of a data object saved in the backend, and it may need to add some new fields to use for rendering.

The folder structure looks as follows:

![Screenshot of the frontend project folder structure in VS Code showing the src directory with subdirectories: components/ (containing AddPatientModal/ and PatientListPage/), services/, App.tsx, types.ts, and the main App component with routing setup](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/VMYxN1A4vFa24il5ZhQENJOhoWwh2E.png)

Besides the component *App* and a directory for services, there are currently three main components: *AddPatientModal* and *PatientListPage* which are both defined in a directory and a component *HealthRatingBar* defined in a file. If a component has some subcomponents not used elsewhere in the app, it might be a good idea to define the component and its subcomponents in a directory. For example, now the AddPatientModal is defined in the file *components/AddPatientModal/index.tsx* and its subcomponent *AddPatientForm* in its own file under the same directory.

There is nothing too surprising in the code. The state and communication with the backend are implemented with *useState* hook and Axios, similar to the notes app in the previous section. [Material UI (opens in a new tab)](https://fullstackopen.com/en/part5/react_router_ui_frameworks#ui-libraries) is used to style the app and the navigation structure is implemented with [React Router (opens in a new tab)](https://fullstackopen.com/en/part5/react_router_ui_frameworks#react-router), both familiar to us from part 5 of the course.

From the typing point of view, there are a couple of interesting things. Component *App* passes the function *setPatients* as a prop to the component *PatientListPage*:

Highlighted lines: 14

Copy to clipboard

```javascript
const App = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  // ...

  return (
    <div className="App">
      <Router>
        <Container>
          <Routes>
            // ...
            <Route path="/" element={
              <PatientListPage
                patients={patients}
                setPatients={setPatients}
              />}
            />
          </Routes>
        </Container>
      </Router>
    </div>
  );
};
```

To keep the TypeScript compiler happy, the props are typed as follows:

Copy to clipboard

```typescript
interface Props {
  patients : Patient[]
  setPatients: React.Dispatch<React.SetStateAction<Patient[]>>
}

const PatientListPage = ({ patients, setPatients } : Props ) => { 
  // ...
}
```

So the function *setPatients* has type *React.Dispatch<React.SetStateAction<Patient[]>>*. We can see the type in the editor when we hover over the function:

![VS Code editor screenshot showing a tooltip that appears when hovering over the setPatients prop, revealing the type annotation React.Dispatch<React.SetStateAction<Patient[]>> highlighted in the editor](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/S1r6jVpxYrHsDMGRYY6DvIVywGDJCu.png)

The [React TypeScript cheatsheet (opens in a new tab)](https://react-typescript-cheatsheet.netlify.app/docs/basic/getting-started/basic_type_example#basic-prop-types-examples) has a pretty nice list of typical prop types, where we can seek help if finding the proper typing for props is not obvious.

*PatientListPage* passes four props to the component *AddPatientModal*. Two of these props are functions. Let us have a look at how these are typed:

Highlighted lines: 8, 13, 23, 25

Copy to clipboard

```typescript
const PatientListPage = ({ patients, setPatients } : Props ) => {
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [error, setError] = useState<string>();
  // ...
  const closeModal = (): void => {
    setModalOpen(false);
    setError(undefined);
  };

  const submitNewPatient = async (values: PatientFormValues) => {
    // ...
  };

  // ...

  return (
    <div className="App">
      // ...
      <AddPatientModal
        modalOpen={modalOpen}
        onSubmit={submitNewPatient}
        error={error}
        onClose={closeModal}
      />
    </div>
  );
};
```

Types look like the following:

Copy to clipboard

```typescript
interface Props {
  modalOpen: boolean;
  onClose: () => void;
  onSubmit: (values: PatientFormValues) => Promise<void>;
  error?: string;
}

const AddPatientModal = ({ modalOpen, onClose, onSubmit, error }: Props) => {
  // ...
}
```

*onClose* is just a function that takes no parameters and does not return anything, so the type is:

Copy to clipboard

```dart
() => void
```

"The type of `onSubmit` is a bit more interesting. It takes a single parameter of type `PatientFormValues` and, since it is an async function, returns a `Promise`. Because the function doesn't return a value, the full type is:

Copy to clipboard

```livescript
(values: PatientFormValues) => Promise<void>
```

## Exercise: 23. Patientor, step 1

Tries: 1

Points: 0/1

Instructions

We will soon add a new type for our app, *Entry*, which represents a lightweight patient journal entry. It consists of a journal text, i.e. a *description*, a creation date, information regarding the specialist who created it and possible diagnosis codes. Diagnosis codes map to the ICD-10 codes returned from the */api/diagnoses* endpoint. Our naive implementation will be that a patient has an array of entries.

Before going into this, we need some preparatory work.

Create an endpoint */api/patients/:id* to the backend that returns all of the patient information for one patient, including the array of patient entries that is still empty for all the patients. For the time being, expand the backend types as follows:

Copy to clipboard

```moonscript
// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface Entry {
}

export interface Patient {
  id: string;
  name: string;
  ssn: string;
  occupation: string;
  gender: Gender;
  dateOfBirth: string;
  entries: Entry[]
}

export type NonSensitivePatient = Omit<Patient, 'ssn' | 'entries'>;
```

The response should look as follows:

![JSON response from the /api/patients/:id endpoint shown in the browser, displaying a patient object with fields: id, name, ssn, occupation, gender, dateOfBirth, and an empty entries array](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/rti09yIHpyiZQ2Op3U3jN5NkLFhh4B.png)

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 24. Patientor, step 2

Tries: 1

Points: 0/1

Instructions

Create a page for showing a patient's full information in the frontend.

The user should be able to access a patient's information by clicking the patient's name.

Fetch the data from the endpoint created in the previous exercise.

You may use [MaterialUI (opens in a new tab)](https://material-ui.com/) for the new components but that is up to you since our main focus now is TypeScript.

You might want to have a look at [part 7 (opens in a new tab)](https://fullstackopen.com/en/part7/react_router) if you don't yet have a grasp on how the [React Router (opens in a new tab)](https://reactrouter.com/en/main/start/tutorial) works.

The result could look like this:

![Simple patient information page UI showing patient details including name, gender (represented by Material UI icon), date of birth, occupation, and SSN, displayed in a clean card-style layout](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/dbKA4bUei1zDa1izzmC14BPmoHzkwx.png)

The example uses [Material UI Icons (opens in a new tab)](https://mui.com/components/material-icons/) to represent genders.

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

### Full entries

In [exercise 11](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-4#5d956dd3-2171-4755-a813-550d9bc68124), we implemented an endpoint for fetching information about various diagnoses, but we are still not using that endpoint at all. Since we now have a page for viewing a patient's information, it would be nice to expand our data a bit. Let's add an *Entry* field to our patient data so that a patient's data contains their medical entries, including possible diagnoses.

Let's ditch our old patient seed data from the backend and start using [this expanded format (opens in a new tab)](https://github.com/fullstack-hy2020/misc/blob/master/patients-full.ts).

Let us now create a proper *Entry* type based on the data we have.

If we take a closer look at the data, we can see that the entries are quite different from one another. For example, let's take a look at the first two entries:

Copy to clipboard

```bash
{
  id: 'd811e46d-70b3-4d90-b090-4535c7cf8fb1',
  date: '2015-01-02',
  type: 'Hospital',
  specialist: 'MD House',
  diagnosisCodes: ['S62.5'],
  description:
    "Healing time appr. 2 weeks. patient doesn't remember how he got the injury.",
  discharge: {
    date: '2015-01-16',
    criteria: 'Thumb has healed.',
  }
}
...
{
  id: 'fcd59fa6-c4b4-4fec-ac4d-df4fe1f85f62',
  date: '2019-08-05',
  type: 'OccupationalHealthcare',
  specialist: 'MD House',
  employerName: 'HyPD',
  diagnosisCodes: ['Z57.1', 'Z74.3', 'M51.2'],
  description:
    'Patient mistakenly found himself in a nuclear plant waste site without protection gear. Very minor radiation poisoning. ',
  sickLeave: {
    startDate: '2019-08-05',
    endDate: '2019-08-28'
  }
}
```

Immediately, we can see that while the first few fields are the same, the first entry has a *discharge* field and the second entry has *employerName* and *sickLeave* fields. All the entries seem to have some fields in common, but some fields are entry-specific.

When looking at the *type*, we can see that there are three kinds of entries:

- *OccupationalHealthcare*
- *Hospital*
- *HealthCheck*

This indicates we need three separate types. Since they all have some fields in common, we might just want to create a base entry interface that we can extend with the different fields in each type.

When looking at the data, it seems that the fields *id*, *description*, *date* and *specialist* are something that can be found in each entry. On top of that, it seems that *diagnosisCodes* is only found in one *OccupationalHealthcare* and one *Hospital* type entry. Since it is not always used, even in those types of entries, it is safe to assume that the field is optional. We could consider adding it to the *HealthCheck* type as well since it might just not be used in these specific entries.

So our *BaseEntry* from which each type could be extended would be the following:

Copy to clipboard

```angelscript
interface BaseEntry {
  id: string;
  description: string;
  date: string;
  specialist: string;
  diagnosisCodes?: string[];
}
```

If we want to finetune it a bit further, since we already have a *Diagnosis* type defined in the backend, we might just want to refer to the *code* field of the *Diagnosis* type directly in case its type ever changes. We can do that like so:

Highlighted lines: 6

Copy to clipboard

```angelscript
interface BaseEntry {
  id: string;
  description: string;
  date: string;
  specialist: string;
  diagnosisCodes?: Diagnosis['code'][];
}
```

As was mentioned [earlier in this part (opens in a new tab)](https://fullstackopen.com/en/part9/first_steps_with_type_script/#the-alternative-array-syntax), we could define an array with the syntax *Array<Type>* instead of defining it *Type[]*. In this particular case writing *Diagnosis['code'][]* starts to look a bit strange so we will decide to use the alternative syntax (that is also recommended by the ESlint rule [array-simple (opens in a new tab)](https://typescript-eslint.io/rules/array-type/#array-simple)):

Highlighted lines: 6

Copy to clipboard

```lasso
interface BaseEntry {
  id: string;
  description: string;
  date: string;
  specialist: string;
  diagnosisCodes?: Array<Diagnosis['code']>;
}
```

Now that we have the *BaseEntry* defined, we can start creating the extended entry types we will actually be using. Let's start by creating the *HealthCheckEntry* type.

Entries of type *HealthCheck* contain the field *HealthCheckRating*, which is an integer from 0 to 3, zero meaning *Healthy* and three meaning *CriticalRisk*. This is a perfect case for a *const as object*. With these specifications, we could write a *HealthCheckEntry* type definition like so:

Copy to clipboard

```typescript
const HealthCheckRating = {
  Healthy: 0,
  LowRisk: 1,
  HighRisk: 2,
  CriticalRisk: 3,
} as const;

type HealthCheckRating = typeof HealthCheckRating[keyof typeof HealthCheckRating];

interface HealthCheckEntry extends BaseEntry {
  type: "HealthCheck";
  healthCheckRating: HealthCheckRating;
}
```

Now we only need to create the *OccupationalHealthcareEntry* and *HospitalEntry* types so we can combine them in a union and export them as an Entry type like this:

Copy to clipboard

```1c
export type Entry =
  | HospitalEntry
  | OccupationalHealthcareEntry
  | HealthCheckEntry;
```

### Omit with unions

An important point concerning unions is that, when you use them with *Omit* to exclude a property, it works in a possibly unexpected way. Suppose that we want to remove the *id* from each *Entry*. We could think of using

Copy to clipboard

```ada
Omit<Entry, 'id'>
```

but [it wouldn't work as we might expect (opens in a new tab)](https://github.com/microsoft/TypeScript/issues/42680). In fact, the resulting type would only contain the common properties, but not the ones they don't share. A possible workaround is to define a special Omit-like function to deal with such situations:

Copy to clipboard

```scala
// Define special omit for unions
type UnionOmit<T, K extends string | number | symbol> = T extends unknown ? Omit<T, K> : never;
// Define Entry without the 'id' property
type EntryWithoutId = UnionOmit<Entry, 'id'>;
```

Now we are ready to put the finishing touches on the app!

## Exercise: 25. Patientor, step 3

Tries: 1

Points: 0/1

Instructions

Define the types *OccupationalHealthcareEntry* and *HospitalEntry* so that they conform to the new example data. Ensure that your backend returns the entries properly when you go to an individual patient's route:

![JSON response from the /api/patients/:id endpoint showing patient data with a populated entries array containing Hospital and OccupationalHealthcare entry objects with fields like id, date, type, specialist, diagnosisCodes, description, discharge, employerName, and sickLeave](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/31cmK1SDRz1YAY5QbHizAwvAdw5r2Q.png)

Use types properly in the backend!

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 26. Patientor, step 4

Tries: 1

Points: 0/1

Instructions

Extend a patient's page in the frontend to list the *date*, *description* and *diagnoseCodes* of the patient's entries.

You can use the same type definition for an *Entry* in the frontend. For these exercises, it is enough to just copy/paste the definitions from the backend to the frontend.

Your solution could look like this:

![Patient page UI showing a listing of medical entries under the patient's information, with each entry displaying its date, description text, and diagnosis codes](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/Lj457b7JjwcY2SKEitJV3HzCE5WJdK.png)

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 27. Patientor, step 5

Tries: 1

Points: 0/1

Instructions

Fetch and add diagnoses to the application state from the */api/diagnoses* endpoint. Use the new diagnosis data to show the descriptions for patients' diagnosis codes:

![Patient page UI showing diagnosis codes alongside their descriptive text labels (e.g., diagnosis code Z57.1 shows "Occupational exposure to radiation" as its description)](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/xRnTJvpKlCCr9FBNUXH2QoyZ1ktxTU.png)

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 28. Patientor, step 6

Tries: 1

Points: 0/1

Instructions

Extend the entry listing on the patient's page to include the Entry's details, with a new component that shows the rest of the information of the patient's entries, distinguishing different types from each other.

You could use eg. [Icons (opens in a new tab)](https://mui.com/components/material-icons/) or some other [Material UI (opens in a new tab)](https://mui.com/) component to get appropriate visuals for your listing.

You should use a *switch case*-based rendering and *exhaustive type checking* so that no cases can be forgotten:

![Code editor screenshot showing a TypeScript switch statement that uses exhaustive type checking on entry types, with case branches for Hospital, OccupationalHealthcare, and HealthCheck entry types, ensuring all possible entry types are handled](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/5QkWpfnb3ni0wGyMjUtFFxqGYys4ub.png)

The resulting entries in the listing *could* look something like this:

![Patient entries listing UI showing different entry types styled distinctly: HealthCheck entries with a health rating indicator (heart icon), OccupationalHealthcare entries with an employer name and sick leave dates, and Hospital entries with discharge date and criteria](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/2Wuo6PtjBV235lmjbrz9skSbQ4TdD3.png)

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 29. Patientor, step 7

Tries: 1

Points: 0/1

Instructions

We have established that patients can have different kinds of entries. We don't yet have any way of adding entries to patients in our app, so, at the moment, it is pretty useless as an electronic medical record.

Your next task is to add endpoint */api/patients/:id/entries* to your backend, through which you can POST an entry for a patient.

Remember that we have different kinds of entries in our app, so our backend should support all those types and check that at least all required fields are given for each type.

In this exercise, you quite likely need to remember [this trick (opens in a new tab)](https://fullstackopen.com/en/part9/grande_finale_patientor#omit-with-unions).

You may assume that only correct diagnostics code values are sent to the backend.

**Hint**: If you have defined the *HealthCheckRating* with a const object

Copy to clipboard

```dart
export const HealthCheckRating = {
  Healthy: 0,
  LowRisk: 1,
  HighRisk: 2,
  CriticalRisk: 3,
} as const;
```

You can not a Zod enum for validation since it does not support *number* values. Instead, yo can use the Zod [union](https://zod.dev/api?id=unions):

Copy to clipboard

```less
z.union([
    z.literal(HealthCheckRating.Healthy),
    z.literal(HealthCheckRating.LowRisk),
    z.literal(HealthCheckRating.HighRisk),
    z.literal(HealthCheckRating.CriticalRisk),
])
```

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 30. Patientor, step 8

Tries: 1

Points: 0/1

Instructions

Now that our backend supports adding entries, we want to add the corresponding functionality to the frontend. In this exercise, you should add a form for adding an entry to a patient. An intuitive place for accessing the form would be on a patient's page.

In this exercise, it is enough to **support one entry type**. All the fields in the form can be just plain text inputs, so it is up to the user to enter valid values.

Upon a successful submission the new entry should be added to the correct patient and the patient's entries on the patient page should be updated to contain the new entry.

Your form might look something like this:

![HealthCheck entry form UI showing input fields for description, date, specialist, and health check rating, with a submit button, displayed on the patient's page](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/Tt5sAU8ibWfb2RWQm1YdeWeFa7sTK7.png)

If a user enters invalid values to the form and backend rejects the addition, show a proper error message to the user

![The same form showing a red error message indicating which field had an invalid value, such as a date format error or missing required field](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/Vn9kuuQcyPHRvsCk8tHTiqEW27pQhk.png)

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 31. Patientor, step 9

Tries: 1

Points: 0/1

Instructions

Extend your solution so that it supports *all the entry types*:

![Entry creation form expanded to support multiple entry types (HealthCheck, Hospital, OccupationalHealthcare) with a type selector and dynamically changing form fields based on the selected entry type](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/30VLvwyvw4I8I0e6sk0h1DG07AUzRp.png)

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 32. Patientor, step 10

Tries: 1

Points: 0/1

Instructions

Improve the entry creation forms so that it makes it hard to enter incorrect dates, diagnosis codes and health rating.

Your improved form might look something like the following. Picking a date with [Input (opens in a new tab)](https://mui.com/material-ui/api/input/) element type [date (opens in a new tab)](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/date):

![Form showing a date picker input field with a calendar dropdown for selecting dates instead of typing them manually](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/7yGqmWpYnjEc73fXwnktbkHhIJPkX2.png)

Health rating is selected with Material UI [select](https://mui.com/material-ui/react-select/):

![Form showing a health rating dropdown select component offering choices: Healthy, LowRisk, HighRisk, CriticalRisk](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/enk4cpTGckl12dwXDCBaMoPd0ZGASC.png)

Diagnostic codes set with Material UI [multiple select (opens in a new tab)](https://mui.com/material-ui/react-select/#multiple-select):

![Multi-select dropdown for diagnosis codes in its closed state, showing selected codes as chips/tags in the input field](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/vt4gEAH9Vp89A4VSCQywDYtFa1snT8.png)

![Multi-select dropdown for diagnosis codes in its open/active state, showing a dropdown list of available ICD-10 diagnosis codes with checkboxes](https://courses.mooc.fi/api/v0/files/course/727b37dd-1ad7-4ffa-971c-d45671eef876/images/anV5eb4qQ3a3Lo06FGTRRmlJOqVXVM.png)

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 33. Patientor, the final check

Tries: 1

Points: 0/1

Instructions

As you might have guessed, it is time to test the Patientor app as a whole. Similar to Exercises [8](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-3#7d395c4f-af73-40ae-a915-01b600ff8f93) and [16](https://courses.mooc.fi/org/uh-cs/courses/full-stack-open-typescript/chapter-4#b6ae0349-ef8d-4191-b97a-ef5d751e8800), run the tests in the directory *patientor-tests*. Tests expect that the frontend is running at port 5173.

Enable test also in GitHub by modifying *.github/workflows/patientor-e2e-tests.yml* as follows:

Highlighted lines: 5

Copy to clipboard

```dts
name: Patientor E2E Tests
on:
  push:
    branches: [ main, master ]
```

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

## Exercise: 34. Your GitHub repository

Tries: 3

Points: 0/1

Instructions

In this exercise, you should only tell us what your exercise repository is.

**Note** that if you are using a private repository, add the GitHub user *mluukkai* as a collaborator. If the repository can not be accessed, your course is not graded.

No submission received for this exercise.

Complete and lock the previous chapter to unlock exercises in this chapter.

### Mark Chapter as Complete

Complete and lock the previous chapter to unlock exercises in this chapter.
