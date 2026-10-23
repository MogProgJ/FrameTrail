"""Pinned RF model/loader foundation. No downloads, job submission or approval."""
import hashlib, importlib.metadata, json, os, sys
from pathlib import Path
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1', DO_NOT_TRACK='1')
import torch
from torch import nn
ROOT = Path(__file__).resolve().parent.parent
# scoped_rf is packaged beside this module.
from scoped_rf import ScopedRFCriterion, remap_classifier, target_from_row, weighted_loss

RF_SHA = 'd81979a9213a2109345158ce9232668df4c1ae52e9b8db3f2ec0a8cbad959b33'
MAPPING_SHA = 'fe743b7b4182cffc190486ad9dbb576afb4610fb37e1db67b0f93dc4fec02524'
CONTRACT = 'frametrail-rf-scoped-release-v1'

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def build_model(checkpoint, mapping_path):
    if importlib.metadata.version('rfdetr') != '1.11.2': raise ValueError('Require pinned RF-DETR 1.11.2')
    if sha(checkpoint) != RF_SHA or sha(mapping_path) != MAPPING_SHA: raise ValueError('RF checkpoint or semantic mapping changed')
    from rfdetr import RFDETRSmall
    wrapper = RFDETRSmall(pretrain_weights=str(checkpoint), device='cpu')
    model = wrapper.model.model
    # Preserve the pretrained inference group. Stock train mode otherwise uses 13 groups.
    # Slice all coordinated parameters/modules; changing only a group_detr integer is unsafe.
    for name in ('query_feat', 'refpoint_embed'):
        original = getattr(model, name)
        replacement = nn.Embedding.from_pretrained(original.weight[:model.num_queries].detach().clone(), freeze=False)
        setattr(model, name, replacement)
    transformer = model.transformer
    for name in ('enc_output', 'enc_output_norm', 'enc_out_bbox_embed', 'enc_out_class_embed'):
        modules = getattr(transformer, name)
        setattr(transformer, name, nn.ModuleList([modules[0]]))
    for module in model.modules():
        if hasattr(module, 'group_detr'): module.group_detr = 1
    mapping = read(mapping_path)
    model.class_embed = remap_classifier(model.class_embed, mapping['rows'], 615)
    transformer.enc_out_class_embed = nn.ModuleList([remap_classifier(transformer.enc_out_class_embed[0], mapping['rows'], 615)])
    return model

def validate_release(path):
    """A real run must consume a separately approved, partitioned release, never drafts."""
    path = Path(path).resolve(strict=True); manifest = read(path)
    if manifest.get('contract') != CONTRACT or manifest.get('approved_for_training') is not True:
        raise ValueError('A reviewed release is required; proposals/drafts are not training approvals')
    if manifest.get('weak_policy') not in ('excluded', 'approved-training-only-quarter-weight'):
        raise ValueError('Missing explicit weak-label policy')
    groups, ids, hashes, split_counts = {}, set(), set(), {'train':0,'val':0,'test':0}
    for row in manifest['images']:
        split = row['split']; kind = row['supervision']
        if split not in split_counts or kind not in ('gold', 'weak'): raise ValueError('Unknown partition/supervision')
        if row['image_id'] in ids or row['image_sha256'] in hashes: raise ValueError('Duplicate image/bytes across partitions')
        ids.add(row['image_id']); hashes.add(row['image_sha256'])
        group = row['identity_group']
        if group in groups and groups[group] != split: raise ValueError('Author identity leaks across partitions')
        groups[group] = split; split_counts[split] += 1
        if kind == 'weak':
            if manifest['weak_policy'] != 'approved-training-only-quarter-weight' or split != 'train' or row['loss_weight'] != .25:
                raise ValueError('Weak supervision is restricted to approved train-only quarter weight')
            if any(state != 'positive_only' for state in row['scope'].values()): raise ValueError('Weak labels cannot establish absence/completeness')
        elif row['loss_weight'] != 1: raise ValueError('Gold target weighting changed')
        target_from_row(row, 615)
        if not row['targets'] and not any(v == 'absent' for v in row['scope'].values()): raise ValueError('Unknown scene cannot be treated as a negative')
        relative = Path(row['source_path'])
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('Use contained, relative release photos')
        photo = (path.parent / relative).resolve(strict=True)
        if not photo.is_relative_to(path.parent) or sha(photo) != row['image_sha256']: raise ValueError('Photo bytes/path changed')
        if row.get('rights_verified_private_research') is not True: raise ValueError('Individual source rights gate missing')
        receipt_relative = Path(row['rights_receipt_path'])
        if receipt_relative.is_absolute() or '..' in receipt_relative.parts: raise ValueError('Rights receipt escaped release')
        receipt = (path.parent / receipt_relative).resolve(strict=True)
        if not receipt.is_relative_to(path.parent) or sha(receipt) != row['rights_receipt_sha256']: raise ValueError('Rights evidence changed')
        evidence = read(receipt)
        if evidence.get('rights_gate') != 'pass-private-research' or evidence.get('image_sha256') != row['image_sha256']: raise ValueError('Wrong individual rights evidence')
    if not split_counts['train'] or not split_counts['val']: raise ValueError('Reviewed train and validation partitions required')
    return manifest

def load_sample(base, row, device='cpu'):
    from PIL import Image
    from torchvision.transforms import functional as TF
    with Image.open(Path(base) / row['source_path']) as photo:
        if photo.format != 'JPEG' or photo.size != (row['width'], row['height']) or photo.getexif().get(274,1) != 1:
            raise ValueError('Photograph geometry/orientation differs')
        tensor = TF.to_tensor(photo.convert('RGB'))
    tensor = TF.normalize(TF.resize(tensor, [512,512], antialias=False), [.485,.456,.406], [.229,.224,.225])
    return tensor.unsqueeze(0).to(device), target_from_row(row, 615, device)

def scoped_batch_one_loss(model, image, target, loss_weight=1):
    if loss_weight not in (1, .25) or image.shape != (1,3,512,512): raise ValueError('Fixed batch-one/weight contract required')
    outputs = model(image)
    if outputs['pred_logits'].shape != (1,300,616): raise ValueError('Expected one RF query group and canonical output head')
    losses = ScopedRFCriterion(615)(outputs, [target])
    total = weighted_loss(losses) * loss_weight
    if not torch.isfinite(total): raise ValueError('Nonfinite scoped loss')
    return total, losses, outputs
