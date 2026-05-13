param(
  [int]$TestLimit = 2,
  [int]$TrainPositiveLimit = 3,
  [int]$KeywordTopK = 2,
  [int]$VectorTopK = 2,
  [string]$CollectionName = ""
)

$cmd = "uv run python -m backend.scripts.run_eval_smoke --test-limit $TestLimit --train-positive-limit $TrainPositiveLimit --keyword-top-k $KeywordTopK --vector-top-k $VectorTopK"
if ($CollectionName -ne "") {
  $cmd = "$cmd --collection-name $CollectionName"
}
Invoke-Expression $cmd
