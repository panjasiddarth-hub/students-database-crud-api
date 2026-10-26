const rows = document.querySelector("#student-rows");
const count = document.querySelector("#student-count");
const search = document.querySelector("#search");
const emptyState = document.querySelector("#empty-state");
const loadingState = document.querySelector("#loading-state");
const dialog = document.querySelector("#student-dialog");
const form = document.querySelector("#student-form");
const formError = document.querySelector("#form-error");
const toast = document.querySelector("#toast");
let students = [];
let editingId = null;
let toastTimer;

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = "Something went wrong. Please try again.";
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : "Please check the student details and try again.";
    } catch { /* Use the friendly fallback message. */ }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function initials(name) {
  return name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase();
}

function addCell(row, content, className = "") {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  if (content instanceof Node) cell.append(content);
  else cell.textContent = content || "—";
  row.append(cell);
  return cell;
}

function makeStudentRow(student) {
  const row = document.createElement("tr");
  const who = document.createElement("div");
  who.className = "student-cell";
  const avatar = document.createElement("span");
  avatar.className = "avatar";
  avatar.textContent = initials(student.name);
  const identity = document.createElement("span");
  const name = document.createElement("span");
  name.className = "student-name";
  name.textContent = student.name;
  const id = document.createElement("span");
  id.className = "student-sub";
  id.textContent = `Student #${student.student_id}`;
  identity.append(name, id);
  who.append(avatar, identity);
  addCell(row, who);
  addCell(row, student.date_of_birth);
  const course = document.createElement("span");
  course.className = "course-tag";
  course.textContent = student.course || "No course";
  addCell(row, course);
  addCell(row, student.email || student.phone || "—");

  const actions = document.createElement("div");
  actions.className = "row-actions";
  const edit = document.createElement("button");
  edit.className = "icon-button";
  edit.type = "button";
  edit.title = `Edit ${student.name}`;
  edit.setAttribute("aria-label", edit.title);
  edit.textContent = "✎";
  edit.addEventListener("click", () => openDialog(student));
  const remove = document.createElement("button");
  remove.className = "icon-button delete";
  remove.type = "button";
  remove.title = `Delete ${student.name}`;
  remove.setAttribute("aria-label", remove.title);
  remove.textContent = "×";
  remove.addEventListener("click", () => deleteStudent(student));
  actions.append(edit, remove);
  addCell(row, actions);
  return row;
}

function renderStudents() {
  const term = search.value.trim().toLowerCase();
  const filtered = students.filter(student =>
    [student.name, student.course, student.email, student.phone].some(value => value?.toLowerCase().includes(term))
  );
  rows.replaceChildren(...filtered.map(makeStudentRow));
  count.textContent = String(students.length);
  loadingState.hidden = true;
  emptyState.hidden = filtered.length > 0;
  emptyState.querySelector("h3").textContent = students.length ? "No matching students" : "No students yet";
  emptyState.querySelector("p").textContent = students.length ? "Try another name, course, or email." : "Add your first student to get started.";
  document.querySelector("#empty-add").hidden = students.length > 0;
}

async function loadStudents() {
  try {
    students = await request("/students?limit=100");
    renderStudents();
  } catch (error) {
    loadingState.textContent = error.message;
  }
}

function openDialog(student = null) {
  editingId = student?.student_id ?? null;
  form.reset();
  formError.hidden = true;
  document.querySelector("#form-kicker").textContent = editingId ? "EDIT RECORD" : "NEW RECORD";
  document.querySelector("#form-title").textContent = editingId ? "Update student" : "Add a student";
  document.querySelector("#save-student").innerHTML = editingId ? 'Save changes <span aria-hidden="true">→</span>' : 'Save student <span aria-hidden="true">→</span>';
  if (student) {
    for (const field of ["name", "date_of_birth", "email", "phone", "course"]) {
      form.elements[field].value = student[field] || "";
    }
  }
  dialog.showModal();
  form.elements.name.focus();
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2600);
}

async function saveStudent(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form));
  for (const key of Object.keys(data)) if (!data[key]) delete data[key];
  if (!data.email && !data.phone) {
    formError.textContent = "Please add an email or a phone number.";
    formError.hidden = false;
    return;
  }
  const button = document.querySelector("#save-student");
  button.disabled = true;
  try {
    await request(editingId ? `/students/${editingId}` : "/students", {
      method: editingId ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    dialog.close();
    showToast(editingId ? "Student details updated" : "Student added successfully");
    await loadStudents();
  } catch (error) {
    formError.textContent = error.message;
    formError.hidden = false;
  } finally {
    button.disabled = false;
  }
}

async function deleteStudent(student) {
  if (!window.confirm(`Delete ${student.name} from the records?`)) return;
  try {
    await request(`/students/${student.student_id}`, { method: "DELETE" });
    showToast("Student record deleted");
    await loadStudents();
  } catch (error) {
    showToast(error.message);
  }
}

document.querySelector("#add-student").addEventListener("click", () => openDialog());
document.querySelector("#empty-add").addEventListener("click", () => openDialog());
document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
document.querySelector("#cancel-dialog").addEventListener("click", () => dialog.close());
form.addEventListener("submit", saveStudent);
search.addEventListener("input", renderStudents);
document.addEventListener("keydown", event => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    search.focus();
  }
});
loadStudents();
