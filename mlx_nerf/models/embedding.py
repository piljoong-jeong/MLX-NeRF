import mlx.core as mx
import mlx.nn as nn

class Embedder: 
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.create_embedding_func()
        
        return
    
    def create_embedding_func(self):
        """
        
        """

        list_embedding_funcs = []

        in_dim = self.kwargs.get("input_dims", 3)
        out_dim = 0 # NOTE: dynamically determined with hyperparameters
        if self.kwargs["include_input"]:
            list_embedding_funcs.append(lambda x: x)
            out_dim += in_dim

        max_freq = self.kwargs["max_freq_log2"]
        N_freqs = self.kwargs["num_freqs"]
        if self.kwargs["log_sampling"]:
            freq_bands = 2.0 ** mx.linspace(
                0.0, max_freq, steps=N_freqs
            )
        else:
            raise NotImplementedError
        for freq in freq_bands:
            for periodic_func in self.kwargs["periodic_funcs"]:
                list_embedding_funcs.append(
                    lambda x, periodic_func=periodic_func, freq=freq: periodic_func(x * freq)
                )
                out_dim += in_dim
        
        self.embed_funcs = list_embedding_funcs
        self.out_dim = out_dim

        return

    
    def embed(self, inputs):
        return mx.cat(
            [
                embed_func(inputs) for embed_func
                in self.embed_funcs
            ], dim=-1
        )
    
def get_embedder(L):

    if L == -1:
        return nn.Identity(), 3
    
    embed_kwargs = {
        "include_input": True, 
        "input_dims": 3, 
        "max_freq_log2": L-1, 
        "num_freqs": L, 
        "log_sampling": True, 
        "periodic_funcs": [mx.sin, mx.cos],
    }

    embedder_obj = Embedder(**embed_kwargs)
    embedded_sample_generation_func = lambda x, eo=embedder_obj: eo.embed(x)

    return embedded_sample_generation_func, embedder_obj.out_dim
    