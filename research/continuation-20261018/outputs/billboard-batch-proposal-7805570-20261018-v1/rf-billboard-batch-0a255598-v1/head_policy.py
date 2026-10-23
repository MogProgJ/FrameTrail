"""Only explicitly eligible main classifier rows can change; features/boxes stay frozen."""
import hashlib
import torch

def fingerprint_frozen(model):
    digest=hashlib.sha256()
    for name,value in list(model.named_parameters())+list(model.named_buffers()):
        if name in ['class_embed.weight','class_embed.bias']:continue
        digest.update(name.encode());digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()

def configure(model,active,lr):
    for p in model.parameters():p.requires_grad_(False)
    head=model.class_embed
    assert head.out_features==616
    mask=torch.zeros(616,device=head.weight.device);mask[active]=1
    for p in head.parameters():p.requires_grad_(True)
    head.weight.register_hook(lambda g:g*mask[:,None]);head.bias.register_hook(lambda g:g*mask)
    inactive=mask==0
    initial=(head.weight.detach()[inactive].clone(),head.bias.detach()[inactive].clone())
    optimizer=torch.optim.AdamW(head.parameters(),lr=lr,weight_decay=0,foreach=False)
    def check():
        if not torch.equal(head.weight.detach()[inactive],initial[0]) or not torch.equal(head.bias.detach()[inactive],initial[1]):raise ValueError('Inactive classifier rows changed')
    model.eval()
    return optimizer,check
