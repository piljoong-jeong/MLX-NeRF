"""

"""

from argparse import ArgumentParser
from enum import Enum, auto

import numpy as onp
import matplotlib.pyplot as plt
import mlx.core as mx
from tqdm import trange


from mlx_nerf.dataset.dataloader import DatasetType, load_blender_data
from mlx_nerf.integrator import Integrator
from mlx_nerf.rendering import ray, render

class Trainer:

    def __init__(
        self, 
        path_dataset: str, 
        args: ArgumentParser,
    ) -> None:
        
        self.path_dataset = path_dataset
        self.args = args
        
        self.dir_dataset = self.args.datadir

        self.max_iters = 500

        return
    
    def load_dataset(
        self, 
        dataset_type: DatasetType
    ):
        
        func_dataset_loading = {
            DatasetType.BLENDER: load_blender_data, 
        }[dataset_type]

        self.images, self.poses, self.render_poses, self.hwf, self.i_split = func_dataset_loading(self.path_dataset / self.dir_dataset)

        self.i_train, self.i_val, self.i_test = self.i_split
        self.H, self.W, self.focal = self.hwf


    def select_pixels(
        self, 
        batch_size, 
        img_target, 
        H, W, focal, pose
    ):

        K = onp.array([
            [focal, 0, 0.5 * W], 
            [0, focal, 0.5 * H], 
            [0, 0, 1]
        ])
        rays_o, rays_d = ray.get_rays(H, W, K, mx.array(pose))

        rays_o = mx.array(rays_o) # [H, W, 3]
        rays_d = mx.array(rays_d) # [H, W, 3]

        coords = onp.meshgrid(
            onp.arange(0, H), 
            onp.arange(0, W), 
            indexing="ij"
        ) # NOTE: `list`
        
        # TODO: convert all `np.ndarray`s into `mx.array`
        coords[0] = mx.array(coords[0])
        coords[1] = mx.array(coords[1])

        # TODO: stack meshgrids
        coords = mx.stack(coords, axis=-1)
        
        # TODO: reshape, now [H, W] has been flatten
        coords = mx.reshape(coords, [-1, 2])

        choice = mx.array(onp.random.choice(coords.shape[0], size=[batch_size], replace=False)) # NOTE: [H*W]
        selected_coords = coords[choice]

        rays_o = rays_o[selected_coords[:, 0], selected_coords[:, 1]]
        rays_d = rays_d[selected_coords[:, 0], selected_coords[:, 1]]

        batch_rays = mx.stack([rays_o, rays_d], axis=0)
        target_selected = mx.array(img_target[selected_coords[:, 0], selected_coords[:, 1]])[..., :3] # NOTE: remove alpha channel # FIXME: slice earlier

        return batch_rays, target_selected

    def select_pixels_within_image(
        self, 
        batch_size, 
        img_target, 
        H, W, focal, pose
    ):

        K = onp.array([
            [focal, 0, 0.5 * W], 
            [0, focal, 0.5 * H], 
            [0, 0, 1]
        ])
        rays_o, rays_d = ray.get_rays(H, W, K, mx.array(pose))

        rays_o = mx.array(rays_o) # [H, W, 3]
        rays_d = mx.array(rays_d) # [H, W, 3]

        coords = onp.meshgrid(
            onp.arange(0, H), 
            onp.arange(0, W), 
            indexing="ij"
        ) # NOTE: `list`
        
        # TODO: convert all `np.ndarray`s into `mx.array`
        coords[0] = mx.array(coords[0])
        coords[1] = mx.array(coords[1])

        # TODO: stack meshgrids
        coords = mx.stack(coords, axis=-1)
        
        # TODO: reshape, now [H, W] has been flatten
        coords = mx.reshape(coords, [-1, 2])

        choice = mx.array(onp.random.choice(coords.shape[0], size=[batch_size], replace=False)) # NOTE: [H*W]

        for idx_start_chunk in range(0, H*W, batch_size):

            selected_coords = coords[choice[idx_start_chunk:idx_start_chunk+batch_size]]

            rays_o = rays_o[selected_coords[:, 0], selected_coords[:, 1]]
            rays_d = rays_d[selected_coords[:, 0], selected_coords[:, 1]]

            batch_rays = mx.stack([rays_o, rays_d], axis=0)
            target_selected = mx.array(img_target[selected_coords[:, 0], selected_coords[:, 1]])[..., :3] # NOTE: remove alpha channel # FIXME: slice earlier

            yield batch_rays, target_selected

    def train_using(
        self, 
        type_integrator: type,
    ):
        
        assert issubclass(type_integrator, Integrator), f"[ERROR] {type_integrator=} is not an {Integrator} type!"
        integrator = type_integrator((config := None))

        # TODO: move plotting functions so that becomes independent with training code
        # TODO: see how `nerfstudio` handles outputs, say in `get_outputs()`
        fig = plt.figure(figsize=(10, 4))
        list_iters = []
        list_losses_coarse = []
        list_losses_fine = []
        list_rgbs = []; to8b = lambda x: onp.array((mx.clip(x, 0.0, 1.0) * 255.0), copy=False).astype(onp.uint8)

        for i in trange(1, self.max_iters+1):
            idx_img = onp.random.choice(self.i_train)
            X, y = self.select_pixels(
                self.args.N_rand, 
                self.images[idx_img], 
                self.H, self.W, self.focal, 
                self.poses[idx_img, :3, :4])
            
            outputs = integrator.train(X, y)

            list_iters.append(i)
            list_losses_coarse.append(outputs['loss_coarse'].item())
            list_losses_fine.append(outputs['loss_fine'].item())
            

        
        ax1 = fig.add_subplot(1, 2, 1)
        ax1.set_title("Fine Loss validation")
        ax1.plot(list_iters, list_losses_fine)
        

        fig.savefig(f"results/integrator/iter={i}.png")
        
        return
