# from main import compare_with_sentences

# # 기본 (이미 한국어 지원)
# results = compare_with_sentences(
#     query_word="부정",
#     input_file="articles.xlsx",
#     export="result.xlsx"
# )

# # 모델 지정
# results = compare_with_sentences(
#     query_word="부정",
#     input_file="articles.xlsx",
#     model="multilingual",  # 한국어 모델
#     export="result.xlsx"
# )


import torch
print(torch.__version__)
print(torch.version.cuda)   # CUDA 빌드 여부 확인
print(torch.cuda.is_available())
