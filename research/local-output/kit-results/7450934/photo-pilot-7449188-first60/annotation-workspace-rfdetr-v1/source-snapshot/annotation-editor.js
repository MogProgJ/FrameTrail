'use strict';
// Embedded into a self-contained offline HTML file by render_editor().
const payload = JSON.parse(document.getElementById('payload').textContent), seed = payload.seed;
const proposals = payload.proposals || null;
const $ = id => document.getElementById(id), clone = x => structuredClone(x);
function equal(a, b) {
  if (a === b) return true;
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every(k => Object.hasOwn(b, k) && equal(a[k], b[k]));
}
let state = clone(payload.state), index = 0, selected = null, drawing = false, drag = null;
let draft = null, dirty = false, reviewImage = null, backupEvents = state.events.length;
const image = () => state.images[index];
const allBoxes = img => [...img.objects, ...(img.observations || [])];
const object = () => allBoxes(image()).find(x => x.id === selected);
const isObservation = obj => obj && ['manual-observation','model-observation'].includes(obj.origin.kind);
const legacyStorageKey = 'frametrail-annotation-v1-' + seed.source_manifest_sha256;
const storageKey = proposals ? 'frametrail-annotation-rfdetr-v1-'+proposals.pack_id : 'frametrail-annotation-editor-v3-' + seed.source_manifest_sha256;
const classText = raw => seed.classes[raw].name;
const labelText = obj => isObservation(obj) ? obj.label : classText(obj.raw_id);

function validBox(box, img) {
  return Array.isArray(box) && box.length === 4 && box.every(Number.isFinite) &&
    box[0] >= 0 && box[1] >= 0 && box[2] <= img.width && box[3] <= img.height && box[2] > box[0] && box[3] > box[1];
}
function validObject(obj, img) {
  if (!Number.isInteger(obj.raw_id) || obj.raw_id < 0 || obj.raw_id >= seed.classes.length ||
      !validBox(obj.box, img) || !['pending', 'confirmed', 'rejected'].includes(obj.status) ||
      typeof obj.note !== 'string' || (obj.status === 'rejected' && !obj.note.trim()))
    throw Error('Check the label, box boundary and note. Removing a box requires a reason.');
}
function validObservation(obj, img) {
  const modelOrigin = obj.origin && obj.origin.kind === 'model-observation' &&
    equal(Object.keys(obj.origin).sort(),['kind','model','pack_id','candidate_id','confidence','model_sha256'].sort());
  if (!equal(Object.keys(obj).sort(), ['id', 'label', 'box', 'status', 'note', 'origin'].sort()) ||
      typeof obj.label !== 'string' || !obj.label.trim() || obj.label !== obj.label.trim() || obj.label.length > 120 ||
      /[\u0000-\u001f\u007f]/.test(obj.label) || !/^observation-[a-zA-Z0-9-]+$/.test(obj.id) ||
      (!equal(obj.origin, {kind: 'manual-observation'}) && !modelOrigin) || !validBox(obj.box, img) ||
      !['pending', 'confirmed', 'rejected'].includes(obj.status) || typeof obj.note !== 'string' ||
      (obj.status === 'rejected' && !obj.note.trim())) throw Error('Check the observation name, boundary and note.');
  if (seed.classes.some(x => [x.name, x.canonical_name].some(name => name.toLowerCase() === obj.label.toLowerCase())))
    throw Error('This is a supported label. Choose it from the dropdown instead of recording it as outside-model.');
}
function validReview(review) {
  const keys = ['reviewer', 'notes', 'geometry_pass', 'coverage_pass', 'holds', 'rights_evidence'];
  if (!equal(Object.keys(review).sort(), keys.sort()) ||
      !['reviewer', 'notes', 'rights_evidence'].every(x => typeof review[x] === 'string') ||
      !['geometry_pass', 'coverage_pass'].every(x => typeof review[x] === 'boolean') ||
      !Array.isArray(review.holds) || !review.holds.every(x => typeof x === 'string' && x.trim()) ||
      ((review.geometry_pass || review.coverage_pass) && !review.reviewer.trim())) throw Error('Invalid image review fields.');
}
function replay(change, target) {
  if (!equal(Object.keys(change).sort(), ['seq', 'at', 'actor', 'image_id', 'kind', 'object_id', 'before', 'after'].sort()) ||
      typeof change.actor !== 'string' || !change.actor.trim() || typeof change.at !== 'string' || Number.isNaN(Date.parse(change.at)))
    throw Error('Every correction needs a valid editor name and history record.');
  const img = target.images.find(x => x.id === change.image_id);
  if (!img) throw Error('Unknown photograph in correction history.');
  if (change.kind === 'proposal-add') {
    const expected = proposalObject(img.id, change.after.origin.candidate_id);
    if (change.before !== null || change.object_id !== expected.id || !equal(change.after,expected) ||
        allBoxes(img).some(x => x.id === expected.id)) throw Error('RF proposal history/catalogue mismatch or already used.');
    if (isObservation(expected)) { if (!img.observations) img.observations=[]; img.observations.push(clone(expected)); }
    else img.objects.push(clone(expected));
    return;
  }
  if (change.kind === 'review') {
    if (change.object_id !== null || !equal(img.review, change.before)) throw Error('Review history mismatch.');
    validReview(change.after); img.review = clone(change.after); return;
  }
  if (change.kind === 'observation-add' || change.kind === 'observation-update') {
    validObservation(change.after, img);
    if (change.after.id !== change.object_id) throw Error('Observation identity mismatch.');
    const observations = img.observations || [], existing = observations.find(x => x.id === change.object_id);
    if (change.kind === 'observation-add') {
      if (existing || change.before !== null || !equal(change.after.origin,{kind:'manual-observation'})) throw Error('New observations require unique manual IDs.');
      if (!img.observations) img.observations = [];
      img.observations.push(clone(change.after));
    } else {
      if (!existing || !equal(existing, change.before)) throw Error('Observation history mismatch.');
      if (!equal(existing.origin,change.after.origin)) throw Error('Observation provenance cannot be edited.');
      observations[observations.indexOf(existing)] = clone(change.after);
    }
    return;
  }
  const existing = img.objects.find(x => x.id === change.object_id);
  validObject(change.after, img);
  if (change.after.id !== change.object_id) throw Error('Box identity mismatch.');
  if (change.kind === 'add') {
    if (existing || change.before !== null || !/^manual-[a-zA-Z0-9-]+$/.test(change.after.id) ||
        !equal(Object.keys(change.after).sort(), ['id', 'raw_id', 'box', 'status', 'note', 'origin'].sort()) ||
        !equal(change.after.origin, {kind: 'manual'})) throw Error('Invalid manual box provenance.');
    img.objects.push(clone(change.after));
  } else if (change.kind === 'update') {
    if (!existing || !equal(existing, change.before) || !equal(Object.keys(existing).sort(), Object.keys(change.after).sort()))
      throw Error('Box history mismatch.');
    for (const k of Object.keys(existing))
      if (!['raw_id', 'box', 'status', 'note'].includes(k) && !equal(existing[k], change.after[k])) throw Error('Source provenance cannot be edited.');
    img.objects[img.objects.indexOf(existing)] = clone(change.after);
  } else throw Error('Unknown correction type.');
}
function validate(candidate) {
  if (!Array.isArray(candidate.events)) throw Error('Missing correction history.');
  const expected = clone(seed);
  candidate.events.forEach((change, n) => {
    if (change.seq !== n + 1) throw Error('History sequence mismatch.');
    replay(change, expected); expected.events.push(clone(change));
  });
  if (!equal(expected, candidate)) throw Error('Unlogged edits or a different intake/policy.');
  for (const img of candidate.images) {
    validReview(img.review); img.objects.forEach(obj => validObject(obj, img));
    if (img.observations && !Array.isArray(img.observations)) throw Error('Invalid observations.');
    (img.observations || []).forEach(obj => validObservation(obj, img));
    const boxes = allBoxes(img);
    if (new Set(boxes.map(x => x.id)).size !== boxes.length) throw Error('Duplicate box IDs.');
    if ((img.review.geometry_pass || img.review.coverage_pass) && boxes.some(x => x.status === 'pending'))
      throw Error('Uncheck the whole-image passes while boxes are pending. This edit has not been saved.');
  }
  return candidate;
}
function classChoices(query, retained = '') {
  const q = query.trim().toLowerCase();
  return seed.classes.filter(x => String(x.raw_id) === retained ||
    `${x.name} ${x.canonical_name} ${x.raw_id}`.toLowerCase().includes(q)).sort((a, b) => a.name.localeCompare(b.name, 'en'));
}
function createDraft(box, img) {
  if (!validBox(box, img)) throw Error('Drag a positive-area rectangle inside the photo.');
  return {box: clone(box)}; // Deliberately has NO inherited label, note, ID or provenance.
}
function transact(current, imageId, actions, actor, at) {
  const candidate = clone(current);
  for (const action of actions) {
    const img = candidate.images.find(x => x.id === imageId);
    const before = action.kind === 'review' ? img.review : action.kind.endsWith('add') ? null :
      (action.kind.startsWith('observation-') ? img.observations || [] : img.objects).find(x => x.id === action.id);
    const change = {seq: candidate.events.length + 1, at, actor, image_id: imageId,
      kind: action.kind, object_id: action.id, before: clone(before), after: clone(action.after)};
    replay(change, candidate); candidate.events.push(change);
  }
  return validate(candidate); // A failed conversion cannot reject the old box or partially save a new one.
}
function replacementActions(existing, replacement) {
  const after = clone(existing);
  after.status = 'rejected';
  after.note = 'Reclassified as ' + (isObservation(replacement) ? 'outside-model observation ' : 'supported box ') + replacement.id +
    '. Original record preserved. Previous note: ' + existing.note;
  return [{kind: isObservation(existing) ? 'observation-update' : 'update', id: existing.id, after},
    {kind: isObservation(replacement) ? 'observation-add' : 'add', id: replacement.id, after: replacement}];
}
function message(text, error = false) {
  $('message').textContent = text; $('message').style.background = error ? '#ffe5df' : '#eef4f7';
  $('edit-status').textContent = text; $('edit-status').classList.toggle('error', error);
}

function proposalCandidates(imageId = image().id) {
  return proposals ? (proposals.images.find(x => x.image_id === imageId)?.candidates || []) : [];
}
function proposalObject(imageId, id) {
  const p = proposalCandidates(imageId).find(x => x.id === id);
  if (!p) throw Error('This RF proposal is not in the original catalogue.');
  const outside = p.raw_id === null;
  return {id:(outside ? 'observation-' : '')+p.id, box:clone(p.box), status:'pending',
    note:'RF-DETR suggestion: verify label, boundary, duplicates and missed objects.',
    origin:{kind:outside ? 'model-observation' : 'model', model:'RF-DETR Small', pack_id:proposals.pack_id,
      candidate_id:p.id, confidence:p.confidence, model_sha256:proposals.model_sha256},
    [outside ? 'label' : 'raw_id']:outside ? p.name : p.raw_id};
}
function boxIou(a,b) {
  const intersection=Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));
  return intersection/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection);
}
function proposalOverlap(p) {
  return allBoxes(image()).filter(x => x.status !== 'rejected' && boxIou(x.box,p.box)>=.65);
}
function selectProposal(id) {
  guardForm(); const original=proposalObject(image().id,id);
  const existing=allBoxes(image()).find(x=>x.id===original.id);
  selected=existing ? existing.id : null; dirty=false; drawing=false;
  draft=existing ? null : {...createDraft(original.box,image()),proposal_id:id}; render();
  message(existing ? 'This RF suggestion already has a saved decision. Edit it normally.' :
    'RF suggestion selected. Check label/edges and overlapping saved boxes; then Save, Confirm, or write a reason and Remove.');
}
function renderProposals() {
  $('rf-panel').hidden=!proposals;
  if (!proposals) return;
  const list=$('rf-list'); list.replaceChildren();
  const candidates=proposalCandidates(),used=allBoxes(image());
  $('rf-counts').textContent=`${candidates.length} RF suggestions · ${candidates.filter(p=>used.some(x=>x.origin.candidate_id===p.id)).length} saved decisions`;
  for (const p of candidates) {
    const adopted=used.find(x=>x.origin.candidate_id===p.id), overlaps=proposalOverlap(p);
    const button=document.createElement('button');
    button.textContent=`${p.name} · ${(p.confidence*100).toFixed(0)}% score · ${adopted ? adopted.status : overlaps.length ? 'possible duplicate — check' : 'unreviewed'}`;
    button.title=p.raw_id===null ? 'No exact mapping to the current training vocabulary; observation only unless you explicitly choose a supported label.' : 'Unreviewed RF-DETR suggestion';
    button.onclick=safe(()=>selectProposal(p.id)); list.append(button);
  }
  if (!candidates.length) { const p=document.createElement('p'); p.textContent='RF-DETR returned no suggestions. This does NOT mean the image has no objects.'; list.append(p); }
}
function safe(action) { return () => { try { action(); } catch (error) { message(error.message, true); } }; }
function autosave() {
  try { localStorage.setItem(storageKey, JSON.stringify(state)); }
  catch (_) { message('Browser autosave unavailable. Use Save annotations JSON for a durable backup.', true); }
}
function commit(actions) {
  state = transact(state, image().id, actions, $('reviewer').value.trim(), new Date().toISOString());
  const last = actions[actions.length - 1];
  if (last.kind !== 'review') selected = last.id;
  draft = null; dirty = false; drawing = false;
  autosave(); render();
}
function guardForm() {
  if (draft || dirty || drawing || drag) throw Error('Save the current box changes first, or cancel the new box / press Escape to discard unsaved fields.');
}
function svg(name, attributes) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', name);
  Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value)); return node;
}

function renderBoxes() {
  const layer = $('overlay'), img = image();
  layer.replaceChildren(); layer.setAttribute('viewBox', `0 0 ${img.width} ${img.height}`);
  if (proposals && $('show-rf').checked) for (const p of proposalCandidates()) {
    if (allBoxes(img).some(x=>x.origin.candidate_id===p.id)) continue;
    const [x1,y1,x2,y2]=p.box;
    const rect=svg('rect',{x:x1,y:y1,width:x2-x1,height:y2-y1,fill:'transparent',stroke:'#009a9a',
      'stroke-width':2,'stroke-dasharray':'4 3','vector-effect':'non-scaling-stroke'});
    const title=svg('title',{});title.textContent=`RF-DETR: ${p.name} · ${p.confidence.toFixed(3)} · unreviewed`;rect.append(title);
    rect.addEventListener('pointerdown',e=>{if(drawing)return;e.stopPropagation();safe(()=>selectProposal(p.id))();});layer.append(rect);
  }
  const boxes = $('show-boxes').checked ? allBoxes(img).filter(obj =>
    (obj.id === selected || obj.status !== 'rejected' || $('show-rejected').checked) &&
    (obj.id === selected || obj.origin.kind !== 'model' || $('show-model').checked)) : [];
  // Paint selection last, so another large box cannot cover its resize handles.
  boxes.sort((a, b) => Number(a.id === selected) - Number(b.id === selected));
  for (const obj of boxes) {
    const [x1, y1, x2, y2] = obj.box;
    const color = obj.id === selected ? '#ed3b83' : obj.status === 'confirmed' ? '#15a659' :
      isObservation(obj) ? '#7542b7' : obj.origin.kind === 'publisher' ? '#228ae6' : '#ed9c00';
    const rect = svg('rect', {x:x1, y:y1, width:x2-x1, height:y2-y1, fill:'transparent', stroke:color,
      'stroke-width':obj.id === selected ? 3 : 1.5, 'vector-effect':'non-scaling-stroke',
      'stroke-dasharray':isObservation(obj) || obj.status === 'rejected' ? '6 4' : ''});
    const title = svg('title', {}); title.textContent = `${labelText(obj)} · ${obj.status} · ${obj.id}`; rect.append(title);
    rect.addEventListener('pointerdown', e => {
      if (drawing) return;
      e.stopPropagation();
      try { if (selected === obj.id) return; guardForm(); selected = obj.id; render(); }
      catch (error) { message(error.message, true); }
    });
    layer.append(rect);
    if (obj.id === selected && !drawing && obj.status !== 'rejected') {
      for (const [corner, x, y] of [[0,x1,y1],[1,x2,y1],[2,x2,y2],[3,x1,y2]]) {
        const size = img.width * .015;
        const handle = svg('rect', {x:x-size/2, y:y-size/2, width:size, height:size, fill:color,
          stroke:'white', 'stroke-width':1, 'vector-effect':'non-scaling-stroke'});
        handle.style.cursor = 'crosshair';
        handle.addEventListener('pointerdown', e => {
          e.stopPropagation();
          try { guardForm(); drag = {kind:'resize', pointer:e.pointerId, original:clone(obj), corner}; layer.setPointerCapture(e.pointerId); }
          catch (error) { message(error.message, true); }
        }); layer.append(handle);
      }
    }
  }
  if (draft) layer.append(svg('rect', {x:draft.box[0], y:draft.box[1], width:draft.box[2]-draft.box[0],
    height:draft.box[3]-draft.box[1], fill:'transparent', stroke:'#ed3b83', 'stroke-width':3,
    'stroke-dasharray':'5 3', 'vector-effect':'non-scaling-stroke', 'pointer-events':'none'}));
}
function renderList() {
  const img = image(), boxes = allBoxes(img), observations = img.observations || [];
  $('counts').textContent = `${img.objects.filter(x => x.status !== 'rejected').length} supported boxes · ` +
    `${observations.filter(x => x.status !== 'rejected').length} outside-model observations · ` +
    `${boxes.filter(x => x.status === 'pending').length} pending`;
  const list = $('objects'), filter = $('filter').value.trim().toLowerCase(); list.replaceChildren();
  for (const obj of boxes) {
    if (obj.status === 'rejected' && !$('show-rejected').checked && obj.id !== selected) continue;
    if (filter && !`${labelText(obj)} ${obj.id} ${obj.status}`.toLowerCase().includes(filter)) continue;
    const button = document.createElement('button');
    button.textContent = `${labelText(obj)}${isObservation(obj) ? ' — observation' : ''}${obj.origin.model ? ' · RF-DETR' : ''} · ${obj.status}`;
    button.title = obj.id; button.setAttribute('aria-pressed', String(obj.id === selected));
    button.className = (obj.id === selected ? 'selected ' : '') + (obj.status === 'rejected' ? 'rejected' : '');
    button.onclick = safe(() => { if (selected === obj.id) return; guardForm(); selected = obj.id; dirty = false; render(); });
    list.append(button);
  }
  if (!list.children.length) { const p = document.createElement('p'); p.textContent = 'No boxes match this filter.'; list.append(p); }
}
function updatePicker(value = $('class').value) {
  const picker = $('class'), query = $('class-search').value, choices = classChoices(query, value);
  picker.replaceChildren();
  function option(v, text) { const node = document.createElement('option'); node.value = v; node.textContent = text; picker.append(node); }
  option('', 'Choose a label…'); option('outside', 'Other object — outside model label list');
  choices.forEach(x => option(String(x.raw_id), x.name)); picker.value = value;
  if (picker.value !== value) picker.value = '';
  const matches = classChoices(query).length;
  $('class-help').textContent = query ? (matches ? `${matches} matching supported labels. Open the dropdown and choose one.` :
    'No supported label matches. Choose “Other object” to keep an observation; do not substitute Clothing or Necklace.') :
    'Choose from the model’s label list, or “Other object” for an outside-model observation.';
  updateButtons();
}
function searchLabels() {
  dirty = true;
  updatePicker(''); // Searching must not allow confirmation of the old, unrelated label.
  message('Search filters the dropdown. Choose a label or Other object, then Save or Confirm.');
}
function updateButtons() {
  const available = Boolean(draft || object()), outside = $('class').value === 'outside';
  $('outside-fields').hidden = !outside;
  const chosen = outside ? Boolean($('outside-label').value.trim()) : /^\d+$/.test($('class').value);
  $('apply').disabled = !available || !chosen; $('confirm').disabled = !available || !chosen;
  $('apply').textContent = outside ? 'Save observation' : draft ? 'Save new box' : 'Save changes';
  $('confirm').textContent = outside ? 'Confirm observation' : 'Confirm this box';
  $('reject').disabled=!object() && !draft?.proposal_id; $('pending').disabled=!object();
  $('reset').disabled = !object() || isObservation(object()) || !seed.images[index].objects.some(x => x.id === selected);
  $('cancel').hidden = !draft && !drawing && !dirty;
  $('cancel').textContent = draft || drawing ? 'Cancel new box' : 'Discard unsaved fields';
}
function renderForm() {
  const obj = object(), proposed=draft?.proposal_id ? proposalObject(image().id,draft.proposal_id) : null, current = draft || obj;
  $('box-fields').disabled = !current;
  $('edit-heading').textContent = draft ? 'Label your new box' : obj ? `${labelText(obj)} · ${obj.status}` : 'Add or correct a box';
  $('class-search').value = ''; $('outside-label').value = isObservation(obj || proposed) ? (obj || proposed).label : '';
  $('reason').value = (obj || proposed) ? (obj || proposed).note : '';
  ['x1','y1','x2','y2'].forEach((key, n) => $(key).value = current ? current.box[n] : '');
  const source=obj || proposed;
  $('origin').textContent = source ? JSON.stringify({id:source.id, raw_id:source.raw_id, origin:source.origin}, null, 2) : 'New box: not saved until a label is chosen.';
  updatePicker(source ? isObservation(source) ? 'outside' : String(source.raw_id) : '');
  $('rf-duplicate').hidden=!proposed || !proposalOverlap(proposed).length;
  if (proposed) $('rf-duplicate').textContent='Possible duplicate of: '+proposalOverlap(proposed).map(x=>`${labelText(x)} (${x.id}, ${x.status})`).join('; ')+'. Compare saved boxes before adding another target.';
  $('edit-status').classList.remove('error');
  $('edit-status').textContent = draft ? 'Rectangle drawn. Choose its label, then Save or Confirm.' :
    obj ? 'Check the label and edges. Confirm only when this one box is correct.' :
    drawing ? 'Drag a rectangle around the visible object.' : 'Select a box, or click Add a box.';
}
function render() {
  const img = image();
  $('heading').textContent = `${img.number}/${state.images.length} — ${img.anchor} — ${img.id}`;
  if ($('photo').getAttribute('src') !== img.photo_url) $('photo').setAttribute('src', img.photo_url);
  $('photo').alt = `Original photo ${img.number}: ${img.anchor}`;
  $('image-picker').value = String(index); $('previous').disabled = index === 0; $('next').disabled = index === state.images.length-1;
  $('draw').textContent = drawing ? 'Drawing mode — drag a box' : 'Add a box';
  $('overlay').style.cursor = drawing ? 'crosshair' : 'default';
  $('audit').textContent = img.audit || 'See the preserved audit-note files.';
  $('attribution').textContent = JSON.stringify(img.attribution, null, 2);
  $('policy').textContent = Object.values(seed.policy).filter(x => typeof x === 'string').join('\n\n');
  if (reviewImage !== img.id) {
    $('geometry-pass').checked = img.review.geometry_pass; $('coverage-pass').checked = img.review.coverage_pass;
    $('holds').value = img.review.holds.join('\n'); $('review-notes').value = img.review.notes;
    $('rights').value = img.review.rights_evidence; reviewImage = img.id;
  }
  $('history').textContent = state.events.filter(x => x.image_id === img.id).slice(-15)
    .map(x => `${x.seq} ${x.actor}: ${x.kind} ${x.object_id || 'image review'}`).join('\n');
  renderForm(); renderList(); renderBoxes(); renderProposals();
}
function readBox() {
  const box = ['x1','y1','x2','y2'].map(key => $(key).valueAsNumber);
  if (!validBox(box, image())) throw Error('Check the four coordinates: use a nonempty, positive-area rectangle inside the photo.');
  return box;
}
function edit(status = 'pending') {
  if (draft?.proposal_id) {
    const original=proposalObject(image().id,draft.proposal_id), outside=$('class').value==='outside', same=Boolean(isObservation(original))===outside;
    const after=same ? clone(original) : {id:(outside ? 'observation-' : 'manual-')+crypto.randomUUID(),
      origin:{kind:outside ? 'manual-observation' : 'manual'}};
    after.box=readBox(); after.status=status; after.note=$('reason').value;
    if(outside) {after.label=$('outside-label').value.trim();validObservation(after,image());}
    else {if(!/^\d+$/.test($('class').value))throw Error('Choose a supported label or Other object.');after.raw_id=Number($('class').value);validObject(after,image());}
    const actions=[{kind:'proposal-add',id:original.id,after:original}];
    if(same) {if(!equal(after,original))actions.push({kind:outside ? 'observation-update' : 'update',id:original.id,after});}
    else actions.push(...replacementActions(original,after));
    proposalCommit(actions);message('RF decision saved to this session. Download annotations JSON. Check the whole photo for missed objects.');return;
  }
  const existing = object();
  if (!draft && !existing) throw Error('Draw or select a box first.');
  const outside = $('class').value === 'outside', box = readBox(), note = $('reason').value;
  const sameKind = existing && Boolean(isObservation(existing)) === outside;
  let after;
  if (sameKind) after = clone(existing);
  else after = {id:(outside ? 'observation-' : 'manual-') + crypto.randomUUID(),
    box, status, note, origin:{kind:outside ? 'manual-observation' : 'manual'}};
  after.box = box; after.note = existing && !sameKind && note === existing.note ? '' : note; after.status = status;
  if (outside) { after.label = $('outside-label').value.trim(); validObservation(after, image()); }
  else {
    const value = $('class').value;
    if (!/^\d+$/.test(value)) throw Error('Choose a supported label from the dropdown, or choose Other object.');
    after.raw_id = Number(value); validObject(after, image());
  }
  const kind = outside ? (sameKind ? 'observation-update' : 'observation-add') : (sameKind ? 'update' : 'add');
  commit(existing && !sameKind ? replacementActions(existing, after) : [{kind, id:after.id, after}]);
  message(outside ? 'Observation saved. It is outside the model and is excluded from training labels. Download JSON to keep it.' :
    'Box correction saved to this session. Download JSON for a durable backup.');
}
function proposalCommit(actions) {
  if(image().review.geometry_pass || image().review.coverage_pass) {
    const review=clone(image().review);review.geometry_pass=false;review.coverage_pass=false;
    actions.unshift({kind:'review',id:null,after:review});
  }
  reviewImage=null;commit(actions);
}
function formReview() {
  return {reviewer:$('reviewer').value.trim(), notes:$('review-notes').value,
    geometry_pass:$('geometry-pass').checked, coverage_pass:$('coverage-pass').checked,
    holds:$('holds').value.split('\n').map(x => x.trim()).filter(Boolean), rights_evidence:$('rights').value};
}
function reviewChanged() { return !equal({...formReview(), reviewer:image().review.reviewer}, image().review); }
function saveReview() { if (reviewChanged()) commit([{kind:'review', id:null, after:formReview()}]); }
function navigate(n) {
  if (n < 0 || n >= state.images.length) return;
  try { guardForm(); saveReview(); }
  catch (error) { $('image-picker').value = String(index); throw error; }
  index = n; selected = null; drawing = false; drag = null; dirty = false; $('filter').value = '';
  render(); message('Changed photograph. Save a JSON backup before closing.');
}
function point(e) {
  const bounds = $('overlay').getBoundingClientRect();
  return [Math.max(0, Math.min(image().width, (e.clientX-bounds.left)/bounds.width*image().width)),
    Math.max(0, Math.min(image().height, (e.clientY-bounds.top)/bounds.height*image().height))].map(x => Math.round(x*1000)/1000);
}

// UI handlers are kept below the pure logic so they can be tested without a browser.
$('overlay').addEventListener('pointerdown', e => {
  if (!drawing) return;
  drag = {kind:'add', pointer:e.pointerId, start:point(e)};
  $('overlay').setPointerCapture(e.pointerId);
});
$('overlay').addEventListener('pointermove', e => {
  if (!drag || drag.pointer !== e.pointerId) return;
  const p = point(e); let box;
  if (drag.kind === 'add') box = [Math.min(p[0], drag.start[0]), Math.min(p[1], drag.start[1]),
    Math.max(p[0], drag.start[0]), Math.max(p[1], drag.start[1])];
  else {
    box = clone(drag.original.box); box[[0,2,2,0][drag.corner]] = p[0]; box[[1,1,3,3][drag.corner]] = p[1];
  }
  drag.box = box;
  let preview = $('drag-preview');
  if (!preview) {
    preview = svg('rect', {id:'drag-preview', fill:'transparent', stroke:'#ed3b83', 'stroke-width':3,
      'vector-effect':'non-scaling-stroke', 'pointer-events':'none'}); $('overlay').append(preview);
  }
  preview.setAttribute('x', box[0]); preview.setAttribute('y', box[1]);
  preview.setAttribute('width', Math.max(0, box[2]-box[0])); preview.setAttribute('height', Math.max(0, box[3]-box[1]));
});
$('overlay').addEventListener('pointerup', e => {
  if (!drag || drag.pointer !== e.pointerId) return;
  const task = drag; drag = null;
  try {
    const proposal = createDraft(task.box, image());
    if (task.kind === 'add') {
      draft = proposal; selected = null; drawing = false; dirty = false;
      render(); $('class-search').focus(); message('Rectangle drawn. Choose a label from the dropdown, then Save or Confirm.');
    } else {
      const after = clone(task.original); after.box = proposal.box; after.status = 'pending';
      after.note = after.note || 'Boundary resized; recheck this box.';
      commit([{kind:isObservation(after) ? 'observation-update' : 'update', id:after.id, after}]);
      message('Boundary saved; the box is pending again. Check it, then Confirm. Download JSON for a backup.');
    }
  } catch (error) { render(); message(error.message, true); }
});
$('overlay').addEventListener('pointercancel', () => { drag = null; renderBoxes(); });
$('draw').onclick = safe(() => {
  guardForm(); selected = null; draft = null; dirty = false; drawing = true; $('show-boxes').checked = true;
  render(); message('Drag a rectangle around the visible object. You will choose the label afterwards.');
});
function cancelFields() {
  drag = null; draft = null; drawing = false; dirty = false; render();
  message('Unsaved box/fields discarded. Previously saved annotations are unchanged.');
}
$('cancel').onclick = cancelFields;
document.addEventListener('keydown', e => { if (e.key === 'Escape' && (draft || drawing || dirty || drag)) { e.preventDefault(); cancelFields(); } });
$('class-search').oninput = searchLabels;
$('class').onchange = () => {
  dirty = true;
  if ($('class').value === 'outside' && !$('outside-label').value.trim()) $('outside-label').value = $('class-search').value.trim();
  updateButtons(); message('Label selected. Click Save or Confirm to record it.');
};
['outside-label','reason','x1','y1','x2','y2'].forEach(id => $(id).oninput = () => { dirty = true; updateButtons(); });
$('filter').oninput = renderList;
['show-boxes','show-model','show-rejected','show-rf'].forEach(id => $(id).onchange = () => { renderBoxes(); renderList(); });
$('apply').onclick = safe(() => edit()); $('confirm').onclick = safe(() => edit('confirmed'));
$('pending').onclick = safe(() => edit('pending'));
$('reject').onclick = safe(() => {
  if(draft?.proposal_id) {
    const original=proposalObject(image().id,draft.proposal_id),after=clone(original);
    if(!$('reason').value.trim() || $('reason').value.trim()===original.note.trim())throw Error('Write why this RF suggestion should be removed in Box note first.');
    after.status='rejected';after.note=$('reason').value;
    proposalCommit([{kind:'proposal-add',id:original.id,after:original},
      {kind:isObservation(original) ? 'observation-update' : 'update',id:original.id,after}]);
    message('RF suggestion rejected; its prediction and your reason stay in history. Save JSON.');return;
  }
  const obj = object(); if (!obj) throw Error('Select an existing box to remove.');
  if (!$('reason').value.trim() || (obj.status !== 'rejected' && $('reason').value.trim() === obj.note.trim()))
    throw Error('Write why this box should be removed in Box note first.');
  const after = clone(obj); after.status = 'rejected'; after.note = $('reason').value;
  commit([{kind:isObservation(after) ? 'observation-update' : 'update', id:after.id, after}]);
  message('Box removed from active targets; the record and reason remain in history. Save JSON to keep the change.');
});
$('reset').onclick = safe(() => {
  guardForm();
  const original = seed.images[index].objects.find(x => x.id === selected); if (!original) throw Error('This box has no seed record.');
  const after = clone(object()); after.raw_id = original.raw_id; after.box = clone(original.box);
  after.status = 'pending'; after.note = 'Restored seed geometry/class; requires review.';
  commit([{kind:'update', id:after.id, after}]); message('Seed geometry and label restored. Check this box again.');
});
$('previous').onclick = safe(() => navigate(index-1)); $('next').onclick = safe(() => navigate(index+1));
$('image-picker').onchange = safe(() => navigate(Number($('image-picker').value)));
$('save-review').onclick = safe(() => {
  guardForm(); saveReview(); message('Review notes/checklist saved to this session. Download JSON. Training approval remains false.');
});
$('save').onclick = safe(() => {
  guardForm(); saveReview(); validate(state);
  const blob = new Blob([JSON.stringify(state, null, 2)+'\n'], {type:'application/json'}), url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url;
  link.download = 'frametrail-annotations-'+new Date().toISOString().replaceAll(':','-')+'.json';
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
  backupEvents = state.events.length;
  message('JSON download requested. Check your Downloads folder and keep that file. Browser autosave is not a backup.');
});
$('import').onchange = async () => {
  try {
    const file = $('import').files[0]; if (!file) return;
    guardForm();
    if ((state.events.length > backupEvents || reviewChanged()) &&
        !window.confirm('Import replaces this session. Save annotations JSON first to preserve current edits. Replace it now?')) return;
    if (file.size > 25000000) throw Error('Annotation JSON exceeds the 25 MB limit.');
    const candidate = JSON.parse(await file.text()); validate(candidate);
    state = clone(candidate); backupEvents = state.events.length;
    selected = null; reviewImage = null; draft = null; dirty = false; drawing = false; drag = null;
    autosave(); render(); message('Saved JSON imported; correction history checked. Your edits are preserved; RF suggestions remain available separately.');
  } catch (error) { message(error.message, true); }
  $('import').value = '';
};
state.images.forEach((img, n) => {
  const option = document.createElement('option'); option.value = String(n);
  option.textContent = `${img.number} · ${img.anchor} · ${img.id}`; $('image-picker').append(option);
});
try {
  const saved = localStorage.getItem(storageKey) || (!proposals && localStorage.getItem(legacyStorageKey));
  if (saved) {
    const candidate = JSON.parse(saved); validate(candidate);
    if (candidate.events.length >= state.events.length && state.events.every((x, n) => equal(x, candidate.events[n]))) {
      state = candidate; message('Browser autosave restored. Download JSON for a durable backup.');
    } else message('A different/older autosave was left untouched. Import its saved JSON explicitly to resume it.');
  }
} catch (error) { message('Autosave unavailable or invalid: '+error.message+'. Use JSON save/import.', true); }
validate(state); render();
window.addEventListener('beforeunload', e => {
  if (draft || dirty || drawing || drag || state.events.length > backupEvents || reviewChanged()) { e.preventDefault(); e.returnValue = ''; }
});
window.annotationReview = {getState:() => clone(state), validate, validBox, replay};
